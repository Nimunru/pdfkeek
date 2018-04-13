#coding=utf8

'''
Erase Alternate Descriptions of PDF documents
'''

import re, codecs, zlib, chardet, time
from cStringIO import StringIO
import sys, os, io, json, tempfile
import argparse

def ifspace(c):
	if c == 0 or c == 9 or c == 10 or c == 12 or c == 13 or c == 32:
		return True

class extPDF:
	def __init__(self, file):
		self.file = file
		self.key = 'ObjStm'
		self.byte = ''
		self.fline = 'ini'

		return

	def get_byte(self, count=1):
		return self.file.read(count)

	def get_line(self):
		return self.file.readline()

	def extract_Stms(self):
		newfile = open('newfile.pdf','wb')
		rgstr = StringIO()
		while self.fline:#没有到达文件尾
			self.fline = self.get_line()#先按行获取
			newfile.write(self.fline)
			if self.key in self.fline:
				#防止objstm 和 length 不在同一行
				while not re.search(r'Length',self.fline,re.I):
					self.fline = self.get_line()
					newfile.write(self.fline)
				try:
					length = int(re.findall(r'Length (\w+)',self.fline)[0])#获取stream长度
				except Exception as e:
					continue
				while not re.search(r'stream',self.fline,re.I):
					self.fline = self.get_line()
					newfile.write(self.fline)
				self.byte = self.get_byte()#stream后，从非空白字符开始读取特定长度的字节
				# newfile.write(self.byte)
				while ifspace(ord(self.byte)):
					newfile.write(self.byte)
					self.byte = self.get_byte()
				rgstr.write(self.byte)
				rgstr.write(self.get_byte(length-1))
				compressed = rgstr.getvalue()#获取length长度的压缩数据
				newdata = erase_alt(compressed)
				newfile.write(newdata)
				rgstr.seek(0)
				rgstr.truncate()#清空内存流

			else:
				continue
		newfile.close()

'''
zlib解压，擦除alt信息
'''
def erase_alt(compressed):
	data = zlib.decompress(compressed)
	# print data
	p1 = re.compile(r'Alt\s*\((.*?)\)\s*[\/\>]')
	p2 = re.compile(r'Alt\s*\<(.*?)\>\s*[\/\>]')
	n1data = re.sub(p1,'Alt() /',data)
	n2data = re.sub(p2,'Alt<> /',n1data)
	# print n2data
	recompress = zlib.compress(n2data)
	# recompress = zlib.compress(data)

	return recompress

def ForErase(inf, fn):
	#初始化
	extpdf = extPDF(inf)
	#提取obstream
	extpdf.extract_Stms()
	#文件重命名
	os.rename('newfile.pdf','clean_'+fn)

def begin(infile):
	if os.path.isfile(infile):
		try:
			try:
				f = open(infile,'rb')
			except Exception as e:# windows下文件名不可读
				print 'ERROR: ILLEGAL FILENAME'
			print "TARGET: "+infile
			nn = infile.split('/')[-1]
			ForErase(f, nn)
		except Exception as e:
			print e
	elif os.path.isdir(infile):
		filelist = os.listdir(infile)
		if '.DS_Store' in filelist:
			filelist.remove('.DS_Store')
		num = 0
		for file in filelist:
			num += 1
			print str(num)+'. '+file
			try:
				try:
					inf = open(infile+'/'+file,"rb")
				except Exception as e:# windows下文件名不可读
					print 'ERROR: ILLEGAL FILENAME'
					continue
				nn = file.split('/')[-1]
				ForErase(inf, nn)

			except Exception as e:
				print e
				continue
	else:
		print "ERROR: NO SUCH FILE OR DIRECTORY!"
		return

	print "CLEAN FILES SUCCESSFULLY CREATED!"


def main(argv):
	parse = argparse.ArgumentParser()
	parse.add_argument('-f','--inputfile',dest='infile',help='the inputfile name[single file or directory]')

	args = parse.parse_args()

	if not args.infile:
		print "ERROR: NO INPUT!"
		parse.print_help()

	begin(args.infile)

if __name__ == '__main__':

	sys.stderr=tempfile.TemporaryFile()
	main(sys.argv[1:])

	# fn = "./ins/eree.pdf"
	# nn = fn.split('/')[-1]
	# f = open(fn,'rb')
	# ForErase(f, nn)