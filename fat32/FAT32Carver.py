import os, sys

import io
import zipfile
import zlib
import struct

from fat32 import FAT32Parser, u32, u16

u8 = lambda x: struct.unpack("<B", x)[0]

class FAT32Carver(FAT32Parser):
    def carving(self):
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
                    zip_f = MyZipFile(data)
                    for in_fname in zip_f.namelist():
                        in_fdata = zip_f.read(in_fname)
                        if in_fdata is None or len(in_fdata) < 20:
                            in_ftype = "(lack of info)"
                        else:
                            in_ftype = self.parseExt(in_fdata)
                        print("\t{} {}".format(in_fname, in_ftype))
                

    def parseExt(self, data):
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
            zip_f = MyZipFile(data)
            if "[Content_Types].xml" in zip_f.namelist():
                ftype = "office"
                if "word/document.xml" in zip_f.namelist():
                    ftype = "docs"
                elif "xl/workbook.xml" in zip_f.namelist():
                    ftype = "xlsx"
                elif "ppt/presentation.xml" in zip_f.namelist():
                    ftype = "pptx"   
            else:
                ftype = "zip"
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
        elif data[:3] == b"\x49\x44\x33":
            ftype = "mp3"
        elif data[:4] == b"\x01\x00\x00\x00":
            ftype = "emf"
        elif data[:4] == b"\x00\x00\x01\x00":
            ftype = "ico"
        elif data[:3] == b"\x00\x00\x01" and u8(data[4]) in range(0xb0, 0xc0):
            ftype = "mpeg"
        elif data[:4] == "\x52\x49\x46\x46":
            ftype = "wav"
        else:
            return None

        return ftype


class MyZipFile:
    def __init__(self, data):
        self.data = data
        self.in_files = []
        i = 0
        while i + 30 < len(self.data):    # fname_len을 읽는 것을 보장하기 위해.
            fsize = u32(self.data[i + 18 : i + 22])
            fname_len = u16(self.data[i + 26 : i + 28])
            if (i + 30 + fname_len) >= len(self.data):
                break

            extra_len = u16(self.data[i + 28 : i + 30])
            fname = self.data[i + 30 : i + 30 + fname_len]
            fdata_start = i + 30 + fname_len + extra_len

            fsize_or_zero = fsize if (fdata_start + fsize < len(self.data)) else 0    # fdata 영역이 현재 ZipFile의 전체 크기를 넘어가는 경우 방지.
            if (fname_len != 0):
                self.in_files.append({
                    "fname": fname.decode("euc-kr"),
                    "fstart": fdata_start,
                    "fsize": fsize_or_zero
                })
            i = fdata_start + fsize
    

    def namelist(self):
        return [in_file["fname"] for in_file in self.in_files]

    def read(self, fname):
        f = list(filter(lambda f: f["fname"] == fname, self.in_files))[0]
        compressed_data = self.data[f["fstart"]:f["fstart"] + f["fsize"]]
        try:
            return zlib.decompress(compressed_data, wbits=-zlib.MAX_WBITS)
        except:
            return None


if __name__=="__main__":
    if len(sys.argv) < 2:
        print("usage : python {} <path>".format(sys.argv[0]))
    else:
        parser = FAT32Carver(sys.argv[1])
        parser.carving()
