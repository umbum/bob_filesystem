# coding: utf-8
import struct
import sys
import os

u32 = lambda x: struct.unpack("<L", x)[0]
u16 = lambda x: struct.unpack("<H", x)[0]


class FAT32Parser:
    def __init__(self, image_path):    
        self.fd = open(image_path, "rb")
        self.vbr = self.readSectors(0)

    def readSectors(self, sector, count = 1):
        self.fd.seek(sector * 512)   # PhysicalDrive 읽을 때는 f.seek()안에 꼭 512 단위로 넣어주어야 한다.
        return self.fd.read(count * 512)

    ##################### FAT16/32 common
    @property
    def bps(self):
        return u16(self.vbr[11:11+2])  # bytes_per_sector
    @property
    def spc(self):
        return self.vbr[13]  # sector_per_cluster
    @property
    def reserved_sector_cnt(self):
        return u16(self.vbr[14:14+2])
    @property
    def num_of_fats(self):
        return self.vbr[16]
    @property
    def root_dir_entry_cnt(self):
        return u16(self.vbr[17:17+2])
    ##################### FAT32
    @property
    def fat_size(self):    # fat1, fat2's size
        return u32(self.vbr[36:36+4])
    @property
    def root_dir_cluster(self):
        return u32(self.vbr[44:44+4])
    #####################
    def getNumOfRootDirSectors(self):
        return int(((self.root_dir_entry_cnt * 32) + (self.bps - 1)) / self.bps)

    def getFirstDataSector(self):
        return self.reserved_sector_cnt + (self.fat_size * self.num_of_fats) + self.getNumOfRootDirSectors()

    def getSectorFromCluster(self, cluster):
        return (cluster-2)*self.spc + self.getFirstDataSector()

    def getNextCluster(self, start_cluster):
        # parse FAT1 Table
        fat_sector_num = self.reserved_sector_cnt
        next_cluster = start_cluster
        while (fat_sector_num < self.reserved_sector_cnt + self.fat_size and next_cluster != 0x0fffffff):
            fat_data = self.readSectors(fat_sector_num)  # count에 getFirstDataSector() - fat_sector_num만큼 지정해 한 번에 읽을 수도 있지만, 메모리 낭비.
            while (next_cluster != 0x0fffffff and next_cluster*4+4 <= 512):
                yield next_cluster
                next_cluster = u32(fat_data[next_cluster*4:next_cluster*4+4])
                if next_cluster == 0x00000000:
                    yield -1     # err
            fat_sector_num += 1
    
    #######################################

    def parseDirectoryEntry(self, b):
        # b = binary sector data
        ############### common ###############
        sfn = lambda x: x[0:8].decode("euc-kr")
        ext = lambda x: x[8:8+3].decode("euc-kr")
        isDeleted = lambda x: (x[0] == 0xe5)
        attribute = lambda x: x[11]
        isLfn  = lambda x: (attribute(x) == 0x0f)
        isDir  = lambda x: ((attribute(x) & 0x10) == 0x10)
        isFile = lambda x: ((attribute(x) & 0x20) == 0x20)
        firstCluster = lambda x: (u16(x[20:20+2]) << 8) + u16(x[26:26+2])
        fileSize     = lambda x: u32(x[28:28+4])
        ################ lfn #################
        lfn = ""
        lfnName  = lambda x: (lfnName1(x) + lfnName2(x) + lfnName3(x)).split('\x00', 1)[0]
        lfnName1 = lambda x: x[1:1+10].decode("utf-16-le")
        lfnName2 = lambda x: x[14:14+12].decode("utf-16-le")
        lfnName3 = lambda x: x[28:28+4].decode("utf-16-le")
        #####################################
        print("{0:<26}{1:<15}{2:<10}{3:<10}{4:<20}".format("이름", "파일(F)/디렉토리(D)", "시작 클러스터", "파일 사이즈", "지워짐(D) 여부"))
        for i in range(0, len(b), 32):
            e = b[i:i+32]
            if attribute(e) == 0x00:
                break
            elif isLfn(e):
                lfn = lfnName(e) + lfn
                # order는 따로 체크하지 않는데, lfn이 아닌 엔트리를 만날 때 까지 읽어나가면 되기 때문.
            else:
                if lfn is not "":
                    name = lfn
                    lfn = ""
                else:
                    name = sfn(e)

                if isDir(e):
                    f_type = "Dir"
                elif isFile(e):
                    f_type = "File"
                else:
                    f_type = "-"

                if isDeleted(e):
                    del_flag = "Del"
                else:
                    del_flag = "-"
                print("{0:<26}{1:^20}{2:>12}{3:>15}{4:^32}".format(name, f_type,  firstCluster(e), fileSize(e), del_flag))
    

    #######################################
    def close(self):
        self.fd.close()

    def __del__(self):
        self.close()



if __name__=="__main__":
    image_path = input("[*] fat32 partition image path를 입력하세요 : ")
    if (os.path.exists(image_path) == False):
        print("[*] 입력한 경로에 파일이 없습니다")
        sys.exit()

    parser = FAT32Parser(image_path)
    
    for cluster in parser.getNextCluster(parser.root_dir_cluster):
        data = parser.readSectors(parser.getSectorFromCluster(cluster), count=parser.spc)
        parser.parseDirectoryEntry(data)
        if cluster == -1:
            print("err!!!")
            break
