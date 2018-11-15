#coding=utf8

import re, codecs, zlib, chardet
from cStringIO import StringIO
import sys, os, io, json, tempfile
import argparse

'''
判断空白字符
'''
def ifspace(c):
	if c == 0 or c == 9 or c == 10 or c == 12 or c == 13 or c == 32:
		return True
'''
去除多余斜杠
'''
def throw_slash(s):
	# print s
	brackets={'0x5c0x28':'0x28','0x5c0x29':'0x29','0x5c0x3c':'0x3c','0x5c0x3e':'0x3e','0x5c0x5c':'0x5c','0x5c0x6e':'0x0a','0x5c0x72':'0x0d','0x5c0x0d':''}
	k = ''.join(map(lambda x: hex(ord(x)) if len(hex(ord(x))[2:])==2 else hex(ord(x))[:2]+'0'+hex(ord(x))[2:],s))
	# print k
	for br in brackets.keys():
		if br in k:
			k = k.replace(br,brackets[br])
	zs = re.findall(r'0x(.{2})',k)
	y = ''.join(map(lambda x: x.decode('hex'),zs))
	# print y
	return y
'''
处理utf16字符串
'''
def forUTF16(s):
	# print repr(s)
	k0 = ''.join(map(lambda x: hex(ord(x))[2:] if len(hex(ord(x))[2:])==2 else '0'+hex(ord(x))[2:],s))
	head = k0[:4]
	k = k0[4:]
	# print k
	escp = {'5c72':'0d','5c6e':'0a','5c61':'07','5c62':'08','5c66':'0c','5c63':'09','5c76':'0b',
			'5c28':'28','5c29':'29','5c3e':'3e','5c3c':'3c','5c5c':'5c','5c0d':''}
	# print k
	if head=="feff":#大端
		l = 0
		while l <len(k):
			tk = k[l:l+4]
			if tk in escp.keys():
				tk = escp[tk]
				k = k[:l]+tk+k[l+4:]
			if tk=='':
				continue
			else:
				l+=2
	elif head=="fffe":#小端-待验证
		l = 0
		while l <len(k):
			tk = k[l+2:l+4]+k[l:l+2]
			if tk in escp.keys():
				tk = escp[tk]
				k = k[:l]+tk+k[l+4:]
			if tk=='':
				continue
			else:
				l+=2
	# print k

	a = '\u'
	b=re.findall(r'.{4}',k)
	a += '\u'.join(b)
	# print a

	#编码并拼接
	r = a.decode('unicode_escape').encode('utf-8')
	# print r
	return r



'''
提取objstm
'''
class extPDF:
	def __init__(self, file):
		self.file = file
		self.key = 'ObjStm'
		self.byte = ''
		self.fline = 'ini'
		self.compresseds = []

		return

	def get_byte(self, count=1):
		return self.file.read(count)

	def get_line(self):
		return self.file.readline()

	def extract_Stms(self):
		rgstr = StringIO()
		while self.fline:#没有到达文件尾
			self.fline = self.get_line()#先按行获取

			if self.key in self.fline:
				#防止objstm 和 length 不在同一行
				while not re.search(r'Length',self.fline,re.I):
					self.fline = self.get_line()
				try:
					length = int(re.findall(r'Length (\w+)',self.fline)[0])
				except Exception as e:
					continue

				while not re.search(r'stream',self.fline,re.I):
					self.fline = self.get_line()
				self.byte = self.get_byte()#stream后，从非空白字符开始读取特定长度的字节
				while ifspace(ord(self.byte)):
					self.byte = self.get_byte()
				rgstr.write(self.byte)
				rgstr.write(self.get_byte(length-1))
				compressed = rgstr.getvalue()#获取length长度的压缩数据
				rgstr.seek(0)
				rgstr.truncate()#清空内存流

				self.compresseds.append(compressed)

			else:
				continue
		return self.compresseds

def ext_paths_simple(inf):
	pdfContents = inf.readlines()
	_objs = []
	for pdfContent in pdfContents:
		if re.search(r'Alt', pdfContent, re.I):
			_objs.append(pdfContent)

	return _objs

'''
zlib解压，提取alt
'''
def extract_paths(infn):

	objs = []
	nf1 = open(infn, 'rb')
	objs = ext_paths_simple(nf1)

	nf2 = open(infn, 'rb')
	extpdf = extPDF(nf2)
	compresseds = extpdf.extract_Stms()
	# print len(compresseds)
	for x in range(0,len(compresseds)):
		objs.append(zlib.decompress(compresseds[x]))

# 提取路径并解码
	paths = []
	for x in range(0,len(objs)):
		data = objs[x]
		# lf.write(data)
		path = re.findall(r'Alt\s*\((.*?)\)\s*[\/\>]', data, re.I)
		if len(path) == 0:
			path = re.findall(r'Alt\s*\<(.*?)\>\s*[\/\>]', data, re.I)
		if len(path) != 0:
			rpath = []
			for p in xrange(0,len(path)):
				if re.search(r'[^\xfe\xff\x00+\s+]',path[p]) == None:#非空
					continue
				else:
					# print path[p]
					ea = re.compile('[\x00\s]+$')
					path[p] = ea.sub('',path[p])

					if chardet.detect(path[p])['encoding'] == 'UTF-16':
						rpath.append(forUTF16(path[p]))

					elif chardet.detect(path[p])['encoding']=='ascii' and re.match(r'[^a-e0-9]', path[p], re.I) == None and len(path[p])>4:
						try:
							dp = path[p].decode('hex')
							if chardet.detect(dp)['encoding'] != 'ascii':
								rpath.append(path[p])
							else:
								rpath.append(dp)
							continue
						except Exception as e:
							rpath.append(path[p])
							continue
					else:
						try:
							up = path[p].decode(chardet.detect(path[p])['encoding'],'ignore').encode('utf-8')
							rpath.append(up)
						except Exception as e:
							rpath.append(path[p])

			paths += rpath

	return paths

def begin(infile,outfile,outjson):

	screen = False
	resjson = {}
	if outfile:
		pathfile = open(outfile,'w')
	if outjson:
		pathjson = open(outjson,'w')
	if (not outfile) and (not outjson):
		screen = True
	bfs = open('badfiles.txt','a')
	if os.path.isfile(infile):
		resjson['paths'] = []
		try:
			try:
				f = open(infile,'rb')
			except Exception as e:# windows下文件名不可读
				print 'ERROR: ILLEGAL FILENAME'
			print "TARGET: "+infile
			if outjson:
				resjson['id'] = 1
				resjson['filename'] = infile
			res = extract_paths(infile)
			for r in res:
				r = throw_slash(r)
				da = re.compile('(\x00\x00)+|(\x00\s){2,}')
				r = da.sub('',r)
				# print repr(r)
				if outfile:
					pathfile.write(r+'\r\n')
				if outjson:
					resjson['paths'].append(r)
					pass
				elif screen:
					print r
			if outjson:
				json.dump(resjson,pathjson,ensure_ascii=False)
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
					bfs.write(file+'\n')
					continue
				if outfile:
					pathfile.write('\n============['+str(num)+'] '+file+'============\r\n')
				if outjson:
					resjson['paths'] = []
					resjson['id'] = num
					resjson['filename'] = file
				res = extract_paths(infile+'/'+file)

				for r in res:
					r = throw_slash(r)
					da = re.compile('(\x00\x00)+|(\x00\s){2,}')
					r = da.sub('',r)
					if outfile:
						pathfile.write(r+'\r\n')
					if outjson:
						resjson['paths'].append(r)
					elif screen:
						print r
				if outjson:
					json.dump(resjson,pathjson,ensure_ascii=False)
					pathjson.write('\n')

			except Exception as e:
				print e
				continue
	else:
		print "ERROR: NO SUCH FILE OR DIRECTORY!"
		return

	if outfile:
		print "RESULTS HAVE WRITTEN IN: "+outfile
		pathfile.close()
	if outjson:
		print "RESULTS HAVE WRITTEN IN: "+outjson
		pathjson.close()
	print "ERROR FILES IN: badfiles.txt"
	bfs.close()

def main(argv):
	parse = argparse.ArgumentParser()
	parse.add_argument('-f','--inputfile',dest='infile',help='the inputfile name[single file or directory]')
	parse.add_argument('-o','--outputfile',dest='outfile',help='the outputfile')
	parse.add_argument('-j','--outputjson',dest='outjson',help='the output json file')

	args = parse.parse_args()

	if not args.infile:
		print "ERROR: NO INPUT!"
		parse.print_help()

	begin(args.infile,args.outfile,args.outjson)


if __name__ == '__main__':
	sys.stderr=tempfile.TemporaryFile()
	main(sys.argv[1:])
