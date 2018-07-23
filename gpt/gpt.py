# coding: utf-8
import struct
import sys
import os

u32 = lambda x: struct.unpack('<L', x)[0]
u64 = lambda x: struct.unpack('<Q', x)[0]

class GptParser:
    def __init__(self, image_path):
        self.fd = open(image_path, 'rb')
        self.partition_cnt = 0
    
    def read_sectors(self, sector, count = 1):
        self.fd.seek(sector * 512)   # PhysicalDrive 읽을 때는 f.seek()안에 꼭 512 단위로 넣어주어야 한다.
        return self.fd.read(count * 512)

    def print_partitions(self):
        get_guid = lambda x: x[0:16]
        get_first_LBA = lambda x: u64(x[32:40])
        get_last_LBA = lambda x: u64(x[40:48])
        get_size = lambda x: u64(x[40:48]) - u64(x[32:40])
        
        gpt_header = self.read_sectors(1)       # 1 is GPT Header sector.
        partition_entries_start_sector = u64(gpt_header[72:80])
        num_of_partition_entries = u32(gpt_header[80:84])
        size_of_partition_entries = u32(gpt_header[84:88])
        
        partition_entries_sector = partition_entries_start_sector
        
        current_guid = 0xabcd    # 0이 아닌 아무 값으로 초기화
        while (current_guid != 0):
            partition_entries_raw = self.read_sectors(partition_entries_sector)
            partition_entries = [partition_entries_raw[j:j+128] for j in range(0, 512, 128)]
            i = 0
            current_guid = u64(get_guid(partition_entries[i][:8]))
            while (current_guid != 0):    # 상위 8byte만 비교해도 충분할 것 같아 이렇게 처리.
                self.partition_cnt += 1
                print("partition {} : ".format(self.partition_cnt))
                print("    start LBA : {}".format(get_first_LBA(partition_entries[i])))
                print("    size      : {}".format(get_size(partition_entries[i])))
                i += 1
                if (i > 3):
                    break
                else:
                    current_guid = u64(get_guid(partition_entries[i][:8]))
            partition_entries_sector += 1

        print("[*] End of entry chain")

        
    def close(self):
        self.fd.close()

    def __del__(self):
        self.close()


if __name__=="__main__":
    # physical drive path : "\\\\.\\PhysicalDrive0"
    image_path = input("[*] gpt image path를 입력하세요 : ")
    if (os.path.exists(image_path) == False):
        print("[*] 입력한 경로에 파일이 없습니다")
        sys.exit()

    parser = GptParser(image_path)
    parser.print_partitions()

