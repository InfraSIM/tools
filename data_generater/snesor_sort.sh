#!/bin/bash

# Convert initial sensor dump so that it is one byte on each line
hexdump -v -e '8/1 "0x%02x " " \\\n"' rj_sensors | sed "s/\\\ //g" | sed "s/\\\//g" | sed "s/0x //g" > sensors_tmp
cat sensors_tmp  | tr ' ' '\012' | sed '/^$/d' > sensors_tmp2

# Initialize variables before for loop
sensor_byte=1
body_byte=1
sensor_length=0
sensor_num=1
line_count=1
num_lines=1
mc_addr="0x20"
lun="0x0"
value="0x0"
gen_event="0x1"
sensor_index="0x01"
record_type="0x0"
echo "Processing sensor data..."
for line in `cat sensors_tmp2`
do
    # Update file for SDR sensor (sdr_sensor<sensor_num>) one byte at a time
    # Adhering to format used in .emu file for ipmi_sim
    mod=$(($body_byte % 16))
    if [ $mod -eq 0 ] || [ $sensor_byte -eq 5 ] || [ $sensor_byte -eq $sensor_length ]; then
        echo $line >> sdr_sensor$sensor_num
    else
        echo $line | tr -d "\n" >> sdr_sensor$sensor_num
    fi

    # Get the record type at offset 0x4 in the sensor record
    if [ $sensor_byte -eq 4 ]; then
        record_type=$line
        #echo "Record type is $line"
    fi

    # Get total length of SDR record (sensor_length) and set the starting coutn of the body
    if [ $sensor_byte -eq 5 ]; then
        #echo "Record length is $line"
        hex_length=`echo $line | sed "s/0x//" | tr '[:lower:]' '[:upper:]'`
        sensor_length=`echo "ibase=16; $hex_length"|bc`
        #echo "Sensor length (decimal) is: $sensor_length"
        sensor_length=`expr $sensor_length + 5`
        body_byte=1
    fi

    if [ $sensor_byte -eq 8 ]; then
        sensor_index=$line
        echo "sensor num: $line"
    fi

    # Get sensor support information from SDR byte 12
    if [ $sensor_byte -eq 12 ]; then
	sen_sup=`echo $line | sed "s/0x//" | tr '[:lower:]' '[:upper:]'`
	sen_sup_dec=`echo "ibase=16; $sen_sup" | bc`
	sen_sup_masked=$(($sen_sup_dec & 12))

	if [ $sen_sup_masked -eq 0 ]; then
	    sensor_support="none"
	elif [ $sen_sup_masked -eq 4 ]; then
	    sensor_support="readable"
	elif [ $sen_sup_masked -eq 8 ]; then
	    sensor_support="settable"
	elif [ $sen_sup_masked -eq 12 ]; then
	    sensor_support="fixed"
	else
	    sensor_support=""
	fi
    fi

    # For type 1 sensors, get threshold information
    if [ "$record_type" == "0x01" ] || [  "$record_type" == "0x02" ]; then
        # Get threshold enable byte and convert enable byte to bits
        if [ $sensor_byte -eq 19 ]; then
	    thr=`echo $line | sed "s/0x//" | tr '[:lower:]' '[:upper:]'`
	    thr_en=`echo 16 i 2 o $thr p | dc`

	    # Make sure there are 6 bits
	    count=`echo $thr_en | wc -c`
	    while [ $count -lt 7 ]; do
		thr_en=`echo $thr_en | sed "s/^/0/"`
		count=`echo $thr_en | wc -c`
	    done

	    if [ $count -gt 7 ]; then
		cnt_hi=`echo "$[$count-1]"`
		cnt_lo=`echo "$[$count-6]"`
		thr_en=`echo $thr_en | cut -c $cnt_lo-$cnt_hi`
	    fi
        fi

        # Get threshold bytes
        if [ $sensor_byte -eq 37 ]; then
	    unr=$line
        fi
        if [ $sensor_byte -eq 38 ]; then
            ucr=$line
        fi
        if [ $sensor_byte -eq 39 ]; then
            unc=$line
        fi
        if [ $sensor_byte -eq 40 ]; then
            lnr=$line
        fi
        if [ $sensor_byte -eq 41 ]; then
            lcr=$line
        fi
        if [ $sensor_byte -eq 42 ]; then
            lnc=$line
        fi

	# Get assertion/deassertion bits
	if [ $sensor_byte -eq 15 ]; then
            byte15=`echo $line | sed "s/0x//" | tr '[:lower:]' '[:upper:]'`
        fi
	if [ $sensor_byte -eq 16 ]; then
            byte16=`echo $line | sed "s/0x//" | tr '[:lower:]' '[:upper:]'`
	    byte16_dec=`echo "ibase=16; $byte16" | bc`
	    byte16_masked=$(($byte16_dec & 15))
	    byte16_masked_hex=`echo "obase=16; $byte16_masked" | bc`
	    assert=$byte16_masked_hex$byte15
	    assert=`echo 16 i 2 o $assert p | dc`
	    #echo "Assert is $assert"
	    
	    # Make sure there are 15 bits
            count=`echo $assert | wc -c`
            while [ $count -lt 16 ]; do
                assert=`echo $assert | sed "s/^/0/"`
                count=`echo $assert | wc -c`
            done

        fi
	
	if [ $sensor_byte -eq 17 ]; then
            byte17=`echo $line | sed "s/0x//" | tr '[:lower:]' '[:upper:]'`
        fi
        if [ $sensor_byte -eq 18 ]; then
            byte18=`echo $line | sed "s/0x//" | tr '[:lower:]' '[:upper:]'`
	    byte18_dec=`echo "ibase=16; $byte18" | bc`
            byte18_masked=$(($byte18_dec & 15))
            byte18_masked_hex=`echo "obase=16; $byte18_masked" | bc`
            deassert=$byte18_masked_hex$byte17
            deassert=`echo 16 i 2 o $deassert p | dc`
            #echo "Deassert is $deassert"

	    # Make sure there are 15 bits
            count=`echo $deassert | wc -c`
            while [ $count -lt 16 ]; do
                deassert=`echo $deassert | sed "s/^/0/"`
                count=`echo $deassert | wc -c`
            done
        fi

    fi

    # Increment byte count following the record length field at offset 0x5
    if [ $sensor_byte -gt 5 ]; then
        body_byte=`expr $body_byte + 1`
    fi

    # Check to see if we are at the end of the sensor record
    if [ $sensor_byte -eq $sensor_length ]; then
    #echo "We are at the end of this sensor record"

        # Only process sensor types of 0x01 and 0x02
        if [ "$record_type" != "0x01" ] && [ "$record_type" != "0x02" ]; then
            #echo "Record type is not 0x01 or 0x02 - REMOVE sensor data"
            rm sdr_sensor$sensor_num
        else
            line_count=`cat sdr_sensor$sensor_num | wc -l`
            for line in `cat sdr_sensor$sensor_num`
            do
                if [ $line_count == $num_lines ]; then
                    echo $line | sed  "s/0x/ 0x/g" | sed -e 's/^[ \s]//' >> sdr_sensor$sensor_num.tmp
                else
                    echo $line | sed  "s/0x/ 0x/g" | sed -e 's/^[ \s]//' | sed "s/$/ \\\/g" >> sdr_sensor$sensor_num.tmp
                fi
                num_lines=`expr $num_lines + 1`
            done

            rm sdr_sensor$sensor_num
            mv sdr_sensor$sensor_num.tmp sdr_sensor$sensor_num
            echo "main_sdr_add $mc_addr \\"|cat - sdr_sensor$sensor_num > /tmp/out && mv /tmp/out sdr_sensor$sensor_num

            # Convert sensor ID to hex and put sensor_add at top of the file
            #sensor_num_hex=`echo "obase=16; $sensor_num" | bc`
            #echo "sensor_add $mc_addr $lun 0x$sensor_num_hex $record_type 0x01"|cat - sdr_sensor$sensor_num > /tmp/out && mv /tmp/out sdr_sensor$sensor_num
            #sensor_num_hex=`echo "obase=16; $sensor_index" | bc`
            echo "sensor_add $mc_addr $lun $sensor_index $record_type 0x01"|cat - sdr_sensor$sensor_num > /tmp/out && mv /tmp/out sdr_sensor$sensor_num

            # Add sensor_set_value after each sensor creation (default value of 0)
            #echo "sensor_set_value $mc_addr $lun 0x$sensor_num_hex $value $gen_event" >> sdr_sensor$sensor_num
            echo "sensor_set_value $mc_addr $lun $sensor_index $value $gen_event" >> sdr_sensor$sensor_num

	    if [ "$record_type" == "0x01" ]; then	    
	        echo "sensor_set_threshold $mc_addr $lun $sensor_index $sensor_support $thr_en $unr $ucr $unc $lnr $lcr $lnc" >> sdr_sensor$sensor_num
		echo "sensor_set_event_support $mc_addr $lun $sensor_index enable scanning per-state $assert $deassert $assert $deassert" >> sdr_sensor$sensor_num
		#echo "sensor_set_event_support $mc_addr $lun $sensor_index enable scanning per-state $assert $deassert $assert $deassert"
	    fi

	    if [  "$record_type" == "0x02" ]; then
                echo "sensor_set_threshold $mc_addr $lun $sensor_index $sensor_support $thr_en 0x00 0x00 0x00 0x00 0x00 0x00" >> sdr_sensor$sensor_num
                echo "sensor_set_event_support $mc_addr $lun $sensor_index enable scanning per-state $assert $deassert $assert $deassert" >> sdr_sensor$sensor_num
                #echo "sensor_set_event_support $mc_addr $lun $sensor_index enable scanning per-state $assert $deassert $assert $deassert"
            fi

            # Add blank line in between each sensor
            echo "" >> sdr_sensor$sensor_num
        fi

        # Reset variables for next sensor
        sensor_byte=1
        sensor_length=0
        line_count=1
        num_lines=1
        if [ "$record_type" == "0x01" ] || [ "$record_type" == "0x02" ]; then
            sensor_num=`expr $sensor_num + 1`
        fi
	record_type="0x0"
        continue
    fi

    # Increment byte counter
    sensor_byte=`expr $sensor_byte + 1`
done
# Clean up
rm sensors_tmp sensors_tmp2

total_cnt=`ls sdr_sensor* | wc -l`
echo "Total number of sensors processed (type 0x01 and 0x02): $total_cnt"
echo "Creating one file with all sensors called all_sdr_sensors..."
cat `ls -tr sdr_sensor*` > all_sdr_sensors
rm sdr_sensor*
