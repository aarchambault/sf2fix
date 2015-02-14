#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Analyses LMMS files in input folder, searching for soundfont paths, and 
replaces paths by a valid one if soundfont files do not exist in file system.
Author: Alexis Archambault
License: GPL2
"""

import os
import logging
import shutil
import copy
import zlib
import sys
import getopt
import struct
import xml.etree.ElementTree as etree
from lxml import etree
from os.path import expanduser

DATA_LENGTH_OFFSET = 4
SF2_EXT = "sf2"
MMP_EXT = "mmp"
MMPZ_EXT = "mmpz"
CURRENT_DIR = "."
MODIFIED_MARKER = "_mod"
DEFAULT_SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
LMMS_CONFIG_FILE = ".lmmsrc.xml"
LMMS_CONFIG_FILE_PATHS_TAG = "paths"
LMMS_CONFIG_FILE_SF2_ATTRIBUTE = "defaultsf2"
SF2_PLAYER_TAG = "sf2player"
SF2_PLAYER_PATH_ATTRIBUTE = "src"
SF2_PLAYER_BANK_ATTRIBUTE = "bank"
SF2_PLAYER_PATCH_ATTRIBUTE = "patch"
KIT_MARKER = "kit"
DRUMKIT_BANK = "128"
DRUMKIT_PATCH = "0"

def parse_command_line():
	success = True
	folder = CURRENT_DIR
	soundfont = ""
	try:
		opts, args = getopt.gnu_getopt(sys.argv[1:], "h", ["help"])
	except getopt.GetoptError:
		usage()
		success = False

	if success:
		if not opts:
			if not args:
				usage()
		else:
			for opt, arg in opts:
				if opt in ("-h", "--help"):
					usage()
			
	if success:
		arg_count = len(args)
		can_parse = True
		if arg_count not in (0,1,2) :
			can_parse = False
		
		if can_parse:
			file_to_parse = False
			if arg_count==1:
				first_arg = args[0]
				folder = first_arg
			elif arg_count==2:
				first_arg = args[0]
				second_arg = args[1]
				if identify_file(first_arg, SF2_EXT):
					soundfont = first_arg
					folder = second_arg
				elif identify_file(second_arg, SF2_EXT):
					soundfont = second_arg
					folder = first_arg

	return folder, soundfont
	

def identify_file(path, ext):
    dot_ext = "." + ext
    return path.endswith(dot_ext) or path.endswith(dot_ext.upper())
    
def is_lmms_file(path):
	return identify_file(path, MMP_EXT) or identify_file(path, MMPZ_EXT)

def usage():
	print ("sf2fix - Analyses LMMS files in input folder, searching for \
soundfont paths, and replaces paths by a valid one if soundfont files do \
not exist in file system.")
	print ("Usage: sf2fix.py inputfolder [replacement soundfont]")
	exit(0)

def process_input_paths(folder, soundfont):
	""" Checks validity of input paths """
	if folder is CURRENT_DIR:
		output_folder = os.getcwd()
	else:
		output_folder = folder
	if not soundfont:
		print("Searching soundfont path in LMMS config file...")
		output_soundfont = look_for_lmms_default_soundfount_path()
	else:
		output_soundfont = soundfont
	if not os.path.exists(output_folder) or not os.path.isdir(output_folder):
		print("Input folder does not exist - aborting")
		exit(0)
	if not os.path.exists(output_soundfont):
		print("No valid soundfont - aborting")
		exit(0)
		
	return output_folder, output_soundfont

def look_for_lmms_default_soundfount_path():
	""" Reads LMMS user configuration file, searching for default soundfont path """
	home_dir = expanduser("~")
	lmms_config_file_path = home_dir + os.sep + LMMS_CONFIG_FILE
	output_soundfont = ""
	if os.path.exists(lmms_config_file_path):
		config_file = open(lmms_config_file_path, mode='rb')
		file_data = config_file.read()
		config_file.close()
		root = etree.fromstring(file_data)
		for tag in root.iter(LMMS_CONFIG_FILE_PATHS_TAG):
			soundfont_path = tag.attrib[LMMS_CONFIG_FILE_SF2_ATTRIBUTE]
			if soundfont_path:
				output_soundfont = soundfont_path

	if output_soundfont:
		print ("Found '{0}' in LMMS config file".format(output_soundfont))
	else:
		output_soundfont = DEFAULT_SOUNDFONT
		print ("No path found in LMMS config file - taking default path : {0}".format(output_soundfont))
		
	return output_soundfont
	
def scan_input_folder(folder, replacement_soundfont):
	""" Searches for LMMMS file in input folder """
	if os.path.isdir(folder):
		for filename in os.listdir(folder):
			if is_lmms_file(filename) and MODIFIED_MARKER not in filename:
				print("Analysing {0}...".format(filename))
				process_lmms_file(folder + os.sep + filename, \
					replacement_soundfont)
				print("")


def process_lmms_file(file_path, replacement_soundfont):
	""" Reads a LMMS file, processes XML tree, and creates a new file if
		changes have occurred """
	
	is_mmp_file = identify_file(file_path, MMP_EXT)
	if is_mmp_file:
		file_data = read_mmp_file(file_path)
	else:
		file_data = read_mmpz_file(file_path)
		
	output_file_data, fix_count = \
		scan_song_tree(file_data, replacement_soundfont)
	
	if fix_count:
		basename = os.path.basename(file_path)
		name_without_ext = os.path.splitext(basename)[0]
		extension = os.path.splitext(basename)[1]
		output_file_path = os.path.dirname(file_path) + os.sep \
			+ name_without_ext + MODIFIED_MARKER + extension
		print("Saving output to {0}...".format(output_file_path))
		if is_mmp_file:
			save_mmp_file(output_file_path, output_file_data)
		else:
			save_mmpz_file(output_file_path, output_file_data)
	else:
		print("No fixing done - no new file")

def read_mmp_file(file_path):
	""" Loads an uncompressed LMMS file """
	mmpz_file = open(file_path, mode='rb')
	file_data = mmpz_file.read()
	mmpz_file.close()
	return file_data

def read_mmpz_file(file_path):
	""" Loads a compressed LMMS file (4-byte header + Zip format) """
	mmpz_file = open(file_path, mode='rb')
	mmpz_file.seek(DATA_LENGTH_OFFSET)
	file_data = mmpz_file.read()
	mmpz_file.close()
	uncompressed_data = zlib.decompress(file_data)
	return uncompressed_data

def scan_song_tree(file_data, replacement_soundfont):
	""" Parses file XML content, processes soundfont, and saves back as string """
	fix_count = 0
	is_error = False
	try:
		root = etree.fromstring(file_data)
	except Exception as ex:
		is_error = True
		print("Input file decoding error : " + str(ex))
		
	if not is_error:
		for sf2player in root.iter(SF2_PLAYER_TAG):
			if SF2_PLAYER_PATH_ATTRIBUTE in sf2player.attrib:
				soundfont = sf2player.attrib[SF2_PLAYER_PATH_ATTRIBUTE]
			else:
				soundfont = ""
			if SF2_PLAYER_BANK_ATTRIBUTE in sf2player.attrib:
				bank = sf2player.attrib[SF2_PLAYER_BANK_ATTRIBUTE]
			else:
				bank = -1
			if SF2_PLAYER_PATCH_ATTRIBUTE in sf2player.attrib:
				patch = sf2player.attrib[SF2_PLAYER_PATCH_ATTRIBUTE]
			else:
				patch = -1
			print("Found {0} in XML tree (Bank={1} Patch={2})".format(soundfont, bank, patch))
			if not os.path.exists(soundfont):
				print("    !!! Not in file system - using replacement soundfont")
				sf2player.attrib[SF2_PLAYER_PATH_ATTRIBUTE] = replacement_soundfont
				if KIT_MARKER in soundfont.lower():
					print("    !!! Setting drumkit bank and patch")
					sf2player.attrib[SF2_PLAYER_BANK_ATTRIBUTE] = DRUMKIT_BANK
					sf2player.attrib[SF2_PLAYER_PATCH_ATTRIBUTE] = DRUMKIT_PATCH
				fix_count += 1
		try:
			output = etree.tostring(root, xml_declaration=True, 
			pretty_print=True, encoding='UTF-8')
		except Exception as ex:
			is_error = True
			print("Output file encoding error : " + str(ex))
	
	if is_error:
		output = ""
		
	return output, fix_count

def save_mmp_file(file_path, file_data):
	""" Saves as uncompressed LMMS file """
	mmp_file = open(file_path, mode='wb')
	file_data = mmp_file.write(file_data)
	mmp_file.close()

def save_mmpz_file(file_path, file_data):
	""" Saves as compressed LMMS file (4-byte header + Zip format) """
	mmp_file = open(file_path, mode='wb')
	compressed_data = zlib.compress(file_data)
	mmp_file.write(struct.pack('>I', len(file_data)))
	mmp_file.write(compressed_data)
	mmp_file.close()


if __name__ == '__main__':
	folder, soundfont = parse_command_line()
	folder, replacement_soundfont = process_input_paths(folder, soundfont)
	print("")
	print("Scanned folder is '{0}'".format(folder))
	print("Replacement soundfont is '{0}'".format(replacement_soundfont)) 
	print("")
	scan_input_folder(folder, replacement_soundfont)






