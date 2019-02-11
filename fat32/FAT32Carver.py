import os, sys

import io
import zipfile
from fat32 import FAT32Parser, u32, u16


class FAT32Carver(FAT32Parser):
    def carving(self):
        ftype = "unknown"
        fat_start_sector = self.reserved_sector_cnt
        fat_data = self.readSectors(fat_start_sector, count=self.fat_size)    # get FAT data (FAT1)
        for i in range(0, len(fat_data), 4):
            if (u32(fat_data[i:i+4]) & 0x0fffffff) == 0:    # 0x?0000000이면 free cluster이므로 이를 잡아내기 위해.
                cluster_num = int(i/4)    # free cluster가 FAT에서 몇 번째 cluster인지 알아내고,
                # cluster_num으로 부터 몇 번째 sector인지를 알아내서 read
                data = self.readSectors(self.getSectorFromCluster(cluster_num), count=self.spc)
                ftype = self.parseExt(data)
                if ftype is None:
                    continue
                
                print("{}\t{}".format(cluster_num, ftype))
                if ftype == "zip":
                    dstream = io.BytesIO(data)
                    with zipfile.ZipFile(dstream, 'r') as zip_f:
                        for in_file in zip_f.namelist():
                            in_file_ftype = self.parseExt(zip_f.read(in_file))
                            print("\t{}\t{}".format(in_file, in_file_ftype))


    def parseExt(self, data):
        # TODO : office와 zip을 먼저 해결하고, file signature db에 있는거 파싱해와서 추가
        if data[:2] == b"\xff\xd8":
            ftype = "jpg"
        elif data[:6] in (b"\x47\x49\x46\x38\x37\x61", b"\x47\x49\x46\x38\x39\x61"):
            ftype = "gif"
        elif data[:8] == b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A":
            ftype = "png"
        elif data[:4] == b"\x25\x50\x44\x46":
            ftype = "pdf"
        elif data[:5].lower() == b"<html" or \
            data[:14].lower() == b"<!doctype html":
            ftype = "html"
        elif data[:5] == b"<?xml":
            ftype = "xml"
        elif data[:2] == b"\x42\x4D":
            ftype = "bmp"
        elif data[:2] == b"\x4D\x5A":
            ftype = "PE (exe | dll)"
        elif data[:4] == b"\x50\x4B\x03\x04":
            # zip, pptx, docx, xlsx
            dstream = io.BytesIO(data)
            if zipfile.is_zipfile(dstream):
                with zipfile.ZipFile(dstream, 'r') as zip_f:
                    if "[Content_Types].xml" in zip_f.namelist():
                        ftype = "office"
                        if "word/document.xml" in zip_f.namelist():
                            ftype = "word"
                        elif "xl/workbook.xml" in zip_f.namelist():
                            ftype = "xlsx"
                        elif "ppt/presentation.xml" in zip_f.namelist():
                            ftype = "pptx"
                    else:
                        ftype = "zip"
            else:
                # zip file의 size가 커서 다른 클러스터까지 이어지는 경우. 
                # 바로 다음 클러스터에 이어질 가능성이 크지만, 항상 그럴거라는 보장이 없다.
                # TODO 이런 경우 현재 클러스터에 있는 내용만 파싱해서 보여주고 끝낸다.
                ftype = "zip(cluster size exceeded)"
        elif data[:6] == b"\x37\x7A\xBC\xAF\x27\x1C":
            ftype = "7z"
        elif data[:4] == b"\x41\x4C\x5A\x01":
            ftype = "alz"
        elif data[:6] == b"\x52\x61\x72\x21\x1A\x07":
            ftype = "rar"
        elif data[:17] == b"\x48\x57\x50\x20\x44\x6F\x63\x75\x6D\x65\x6E\x74\x20\x46\x69\x6C\x65":
            ftype = "hwp"
        elif data[:8] == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1":
            # Compound file : hwp, doc, xls, ppt
            ftype = "office"
            if data[512:512+4] == b"\xEC\xA5\xC1\x00":
                ftype = "doc"
            elif data[512:512+4] in (b"\xA0\x46\x1D\xF0", b"\x00\x6E\x1E\xF0", b"\x0F\x00\xE8\x03") or \
               data[512:512+4] == b"\xFD\xFF\xFF\xFF" and data[518:518+3] == b"\x00\x00\x00":
                ftype = "ppt"
            elif data[512:512+8] == b"\x09\x08\x10\x00\x00\x06\x05\x00" or \
               data[512:512+4] == b"\xFD\xFF\xFF\xFF" and data[518] in (b"\x00"):
                ftype = "xls"
            elif b"HWP Document File" in data:
                # OLE 파일을 파싱해서 File Header 스트림의 첫 부분이 HWP Document File 인지 비교하면 더 정확함.
                ftype = "hwp"
        elif data[:4] == b"\x52\x49\x46\x46":
            ftype = "avi"
        elif data[:2] == b"\xFF\xFB":
            ftype = "mp3"
        else:
            return None

        return ftype


if __name__=="__main__":
    # image_path = input("[*] fat32 partition image path를 입력하세요 : ")  
    image_path = "D:\\Source\\bob\\bob_filesystem\\fat32\\DriveE"
    if (os.path.exists(image_path) == False):
        print("[*] 입력한 경로에 파일이 없습니다")
        sys.exit()

    parser = FAT32Carver(image_path)
    parser.carving()
