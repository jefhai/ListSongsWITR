import os
import subprocess
import sys

def write_to_clipboard(output):
    process = subprocess.Popen(
        'pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
    process.communicate(output.encode('utf-8'))

def tear_last_line(file_path):
	file = open(file_path, "r+")
	file.seek(0, os.SEEK_END)
	pos = file.tell()-1
	while pos > 0 and file.read(1) != "\n":
	    pos -= 1
	    file.seek(pos, os.SEEK_SET)
	if pos > 0:
		file.seek(pos, os.SEEK_SET)
		file.truncate()
	file.close()

def main():
	path_to_song_list = str(sys.argv[1])
	if os.path.isfile(path_to_song_list):
		while 1:
			raw_input()
			song = subprocess.check_output(['tail', '-1', path_to_song_list])
			write_to_clipboard(song);
			print "Copied: " + song
			tear_last_line(path_to_song_list)

if __name__ == "__main__":
    main()