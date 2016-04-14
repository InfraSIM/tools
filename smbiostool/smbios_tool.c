#include <stdio.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libgen.h>

// smbios table.
unsigned char *smbios_tables = NULL;
unsigned short smbios_tables_len = 0;
unsigned short smbios_table_max = 0;
unsigned short smbios_table_cnt = 0;

char *system_serial_number = "QTFCKJ9999999";

int debug = 0;

struct smbios_structure_header {
	unsigned char type;
	unsigned char  length;
	unsigned short handle;
} __attribute__ ((packed));

struct dmi_header
{
    struct smbios_structure_header header;
	unsigned char *data;
};

struct smbios_uuid {
    unsigned int time_low;
    unsigned short time_mid;
    unsigned short time_hi_and_version;
    unsigned char clock_seq_hi_and_reserved;
    unsigned char clock_seq_low;
    unsigned char node[6];
} __attribute__ ((packed));

 /* SMBIOS type 1 - System Information */
struct smbios_type_1 {
    struct smbios_structure_header header;
    unsigned char manufacturer_str;
    unsigned char product_name_str;
    unsigned char version_str;
    unsigned char serial_number_str;
    struct smbios_uuid uuid;
    unsigned char wake_up_type;
    unsigned char sku_number_str;
    unsigned char family_str;
} __attribute__((packed));

#define SMBIOS_BUILD_TABLE_PRE(tbl_type, tbl_handle)        \
    struct smbios_type_##tbl_type *t;                                     \
    size_t t_off; /* table offset into smbios_tables */                   \
    int str_index = 0;                                                    \
    do {                                                                  \
        /* use offset of table t within smbios_tables */                  \
        /* (pointer must be updated after each realloc) */                \
        t_off = smbios_tables_len;                                        \
        smbios_tables_len += sizeof(*t);                                  \
        smbios_tables = realloc(smbios_tables, smbios_tables_len);      \
        t = (struct smbios_type_##tbl_type *)(smbios_tables + t_off);     \
                                                                          \
        t->header.type = tbl_type;                                        \
        t->header.length = sizeof(*t);                                    \
        t->header.handle = tbl_handle;                       \
    } while (0)

#define SMBIOS_TABLE_SET_STR(tbl_type, field, value)                      \
    do {                                                                  \
        int len = (value != NULL) ? strlen(value) + 1 : 0;                \
        if (len > 1) {                                                    \
            smbios_tables = realloc(smbios_tables,                      \
                                      smbios_tables_len + len);           \
            memcpy(smbios_tables + smbios_tables_len, value, len);        \
            smbios_tables_len += len;                                     \
            /* update pointer post-realloc */                             \
            t = (struct smbios_type_##tbl_type *)(smbios_tables + t_off); \
            t->field = ++str_index;                                       \
        } else {                                                          \
            t->field = 0;                                                 \
        }                                                                 \
    } while (0)

#define SMBIOS_BUILD_TABLE_POST                                           \
    do {                                                                  \
        size_t term_cnt, t_size;                                          \
                                                                          \
        /* add '\0' terminator (add two if no strings defined) */         \
        term_cnt = (str_index == 0) ? 2 : 1;                              \
        smbios_tables = realloc(smbios_tables,                          \
                                  smbios_tables_len + term_cnt);          \
        memset(smbios_tables + smbios_tables_len, 0, term_cnt);           \
        smbios_tables_len += term_cnt;                                    \
                                                                          \
        /* update smbios max. element size */                             \
        t_size = smbios_tables_len - t_off;                               \
        if (t_size > smbios_table_max) {                                  \
            smbios_table_max = t_size;                                    \
        }                                                                 \
                                                                          \
        /* update smbios element count */                                 \
        smbios_table_cnt++;                                               \
    } while (0)


int checksum(const unsigned char *buf, size_t len)
{
    unsigned char sum = 0;
    size_t a;

    for (a = 0; a < len; a++) {
        sum += buf[a];
    }
    return sum;
}

int smbios_table_entry_add(void *data, int size, unsigned char append_zeros)
{
    struct smbios_structure_header *header;

    if (append_zeros) {
        size += 2;
    }
    smbios_tables = realloc(smbios_tables, smbios_tables_len + size);
    header = (struct smbios_structure_header *)(smbios_tables +
                                                smbios_tables_len);

    memset(header, 0, size);
    memcpy(header, data, append_zeros ? size - 2 : size);

    smbios_tables_len += size;
    if (size > smbios_table_max) {
        smbios_table_max = size;
    }
    smbios_table_cnt++;

    return 0;
}

const char *smbios_string(const struct dmi_header *dm, unsigned char s)
{
    char *bp = (char *)dm->data;
    if (s == 0)
        return "not specified.";

    bp += dm->header.length;
    while (s > 1 && *bp) {
        bp += strlen(bp);
        bp++;
        s--;
    }

    if (!*bp)
        return "bad index";

    return bp;
}

void smbios_build_type_1_table(struct dmi_header *type1)
{
    SMBIOS_BUILD_TABLE_PRE(1, type1->header.handle);
    SMBIOS_TABLE_SET_STR(1, manufacturer_str, smbios_string(type1, type1->data[0x04]));
    SMBIOS_TABLE_SET_STR(1, product_name_str, smbios_string(type1, type1->data[0x05]));
    SMBIOS_TABLE_SET_STR(1, version_str, smbios_string(type1, type1->data[0x06]));
    SMBIOS_TABLE_SET_STR(1, serial_number_str, system_serial_number);

    memcpy(&t->uuid, &type1->data[0x08], 16);
    t->wake_up_type = type1->data[0x18];
    SMBIOS_TABLE_SET_STR(1, sku_number_str, smbios_string(type1, type1->data[0x19]));
    SMBIOS_TABLE_SET_STR(1, family_str, smbios_string(type1, type1->data[0x1a]));
    SMBIOS_BUILD_TABLE_POST;
}

static void to_smbios_header(struct dmi_header *h, unsigned char *data)
{
	h->header.type = data[0];
	h->header.length = data[1];
	h->header.handle = *((unsigned short *)(data + 2));
	h->data = data;
}

// buf -> smbios table structure start address
// len -> smbios table structure length
// num -> total number of table structure 
static void decode_smbios_table(unsigned char *buf, unsigned short len, unsigned short num)
{
    unsigned char *data = buf;
    unsigned int i = 0;

    while ((i < num) && (data + 4 <= buf + len)) {

        struct dmi_header h;
        unsigned char *next = NULL;

        to_smbios_header(&h, data);

        if (debug)
            printf("Type: %d, Length: %d, Handle: 0x%04x\n", h.header.type, h.header.length, h.header.handle);

        if (h.header.length < 4) {
            break;
        }
        
        next = data + h.header.length;
        while (next - buf + 1 < len && (next[0] != 0 || next[1] != 0))
            next++;
        next += 2;

        if (h.header.type == 1) { //type 1
            smbios_build_type_1_table(&h);
        } else {
            smbios_table_entry_add(data, next - data, 0);
        }
        data = next;
        i++;
    }
}

int main(int argc, char *argv[])
{
    char *source_smbios_file = "quanta_smbios.bin";
    char *target_smbios_file = "new_smbios.bin";
    struct stat _stat;
    char *buf = NULL;
    size_t file_size = 0;
    unsigned short structure_table_length = 0;
    unsigned char *structure_table_address = 0;
    unsigned short number_of_smbios_structures = 0;
    char sum = 0;
    int c = -1;
    FILE *fp = NULL;
    FILE *new_fp = NULL;

    while ((c = getopt(argc, argv, "df:s:t:")) != -1) {
        switch (c) {
            case 'f':
                source_smbios_file = optarg;
                break;
            case 's':
                system_serial_number = optarg;
                break;
            case 't':
                target_smbios_file = optarg;
                break;
            case 'd':
                debug = 1;
                break;
            default: 
                printf("%s -f [source smbios file] -s [serial number] -t [target smbios file]\n", basename(argv[0]));
                return;
        }
    }

    if (access(source_smbios_file, F_OK)) {
        printf("%s could be accessed.\n", source_smbios_file);
        return -1;
    }

    if (stat(source_smbios_file, &_stat) < 0) {
        printf("Stat file failed.\n");
        return -1;
    }

    file_size = _stat.st_size;
    printf("smbios file size: %d\n", file_size);

    buf = malloc(file_size);

    if (NULL == buf) {
        printf("Malloc failed.");
        return -1;
    }
    
    fp = fopen(source_smbios_file, "rb+");

    if (NULL == fp) {
        printf("Open smbios file failed.");
        free(buf);
        return -1;
    }

    if (fread(buf, 1, file_size, fp) != file_size) {
        printf("Read failed.\n");
        goto out;
    }

    if (memcmp(buf, "_SM_", 4) != 0) {
        printf("no header!\n");
        decode_smbios_table(buf, file_size, 0xff);
        goto save;
    }

    if (memcmp(buf + 0x10, "_DMI_", 5) != 0) {
        printf("Check _DMI_ failed.\n");
        goto out;
    }

    structure_table_address = buf + 0x20;
    structure_table_length = *((unsigned short *)(buf + 0x16));

    number_of_smbios_structures = *((unsigned short *)(buf + 0x1c));
    
    smbios_table_max = *((unsigned short *)(buf + 0x08));

    printf("smbios table address: 0x%x\n" 
           "smbios table structure length: %d bytes.\n" 
           "smbios structures number: %d\n"
           "smbios maximum structure table %d bytes.\n", 
            structure_table_address, 
            structure_table_length, 
            number_of_smbios_structures, 
            smbios_table_max);

    smbios_tables_len = 32;
    smbios_tables = realloc(smbios_tables, smbios_tables_len);
    memcpy(smbios_tables, buf, 32);

    decode_smbios_table(structure_table_address, 
                        structure_table_length, 
                        number_of_smbios_structures);

    // update smbios structure table length, offset 0x16, two bytes
    *((unsigned short *)(smbios_tables + 0x16)) = smbios_tables_len - 32;
    
    // update maximum structure size, offset 0x08, 2bytes
    //
    *((unsigned short *)(smbios_tables + 0x8)) = smbios_table_max;

    sum = checksum(smbios_tables + 0x10, 0x0F);
    sum -= smbios_tables[0x015];
    smbios_tables[0x15] = (-sum) & 0xff;
 
    //Recalculate checksum, 1 byte, offset 0x04
    sum  = checksum(smbios_tables, smbios_tables[0x05]) & 0xff;
    sum -= smbios_tables[0x04];
    smbios_tables[0x04] = -sum & 0xff;

save:
    new_fp = fopen(target_smbios_file, "wb+");
    fwrite(smbios_tables, 1, smbios_tables_len, new_fp);
    fflush(new_fp);
    fclose(new_fp);
out:
    fclose(fp);
    free(buf);

    return 0;
}
