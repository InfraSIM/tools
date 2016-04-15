import xml.etree.ElementTree as ET
import sys

tree = ET.parse(sys.argv[1])
root = tree.getroot()
for disk in root.findall("devices/disk"):
    source = disk.find('source')
    try:
        if source.get('file') == "disk1":
            source.set('file', sys.argv[2] + "/" + sys.argv[3] + ".qcow2")
        elif source.get('file') == "disk2":
            source.set('file', sys.argv[2] + "/disk2.qcow2")
        else:
            pass
    except:
        pass

tree.write(sys.argv[3] + '-kvm.xml')
