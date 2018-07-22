# coding: utf-8
import struct

p32 = lambda x: struct.pack('<L', x)
u32 = lambda x: struct.unpack('<L', x)[0]

class MbrParser:
    def __init__(self, image_path):
        self.fd = open(image_path, 'rb')
    
    def read_sectors(self, sector, count = 1):
        self.fd.seek(sector * 512)   # PhysicalDrive 읽을 때는 f.seek()안에 꼭 512 단위로 넣어주어야 한다.
        return self.fd.read(count * 512)

    def read(self):
        get_type = lambda x: x[4]
        get_start_addr = lambda x: u32(x[8:12])*512
        get_size = lambda x: u32(x[12:16])*512
        ebr_axis = 0
        partition_axis = 0

        while True:
            boot_record_raw = self.read_sectors(int(partition_axis/512))
            if boot_record_raw[-2] != 0x55 and boot_record_raw[-1] != 0xAA:
                print("이미지의 [0:511] 데이터 조회 결과 MBR 또는 EBR이 아닙니다")
                return -1

            partition_table = boot_record_raw[446:446+64]
            partition_entry = [partition_table[j:j+16] for j in range(0, 64, 16)]
            i = 0
            while (get_type(partition_entry[i]) == 0x07):
                print("partition {}:".format(i))
                print("    LAB addr(byte)      : {}".format(get_start_addr(partition_entry[i]) + partition_axis))
                print("    partiton size(byte) : {}".format(get_size(partition_entry[i])))
                i += 1
            
            if (get_type(partition_entry[i]) == 0x05):
                print("[*] EBR detected")
                # next ebr entry의 주소 + ebr_axis = 다음 ebr 주소.
                partition_axis = get_start_addr(partition_entry[i]) + ebr_axis
                if ebr_axis == 0:
                    # MBR을 파싱하고 partition_table에서 맨 처음 EBR entry를 만났을 때, ebr_axis를 잡아준다.
                    ebr_axis = get_start_addr(partition_entry[i])                    
                # print("    LAB addr(byte)      : {}".format(get_start_addr(partition_entry[i])))
                # print("    partiton size(byte) : {}".format(get_size(partition_entry[i])))
            else:
                print("[*] END of Entry chain")
                break
        
    def close(self):
        self.fd.close()

    def __del__(self):
        self.close()


if __name__=="__main__":
    # physical drive path : "\\\\.\\PhysicalDrive0"
    parser = MbrParser("./mbr/mbr_128.dd")
    parser.read()

