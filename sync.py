#!/usr/bin/python

import os
from os.path import join, expanduser
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.id3 import ID3, APIC, error
from StringIO import StringIO
from PIL import Image

artwork_maxsize = 400, 400
userhome = expanduser("~")

source_dir_default = userhome + '/Music/iTunes/iTunes Media/Music/'

is_valid = False
while not is_valid:
    source_dir = raw_input("Enter source music directory to sync [%s]:"%source_dir_default) or source_dir_default
    is_valid = os.path.isdir(source_dir)
    if not is_valid:
        print "Specified directory path {} doesn't exists.".format(source_dir)

is_valid = False
while not is_valid:
    destination_dir = raw_input("Enter destination directory:")
    is_valid = os.path.isdir(destination_dir)
    if not is_valid:
        print "Specified directory path {} doesn't exists.".format(destination_dir)


print ""
print "Synchronizing directories..."
os.system("rsync --delete --include '*/' --include '*.mp3' --include '*.m4a' --exclude '*' -avuz {0} {1}".format(source_dir.replace(' ', '\ '), destination_dir))

print ""
print "Consolidating album artworks..."
# traverse root directory, and list directories as dirs and files as files
for root, dirs, files in os.walk(destination_dir):
    for file in files:
        filename, extension = os.path.splitext(file)
        filepath = join(root, file)
        if filename[0] != '.' and (extension == '.mp3' or extension == '.m4a'):
            artworks = []
            audio = None
            artwork = None
            artwork_save = False
            artwork_action = False
            artwork_resize = False
            try:
                if extension == '.mp3':
                    audio = MP3(filepath)
                elif extension == '.m4a':
                    audio = MP4(filepath)
            except Exception as error:
                print 'Error while reading file \'{}\':\n {}'.format(file, error)

            if audio:
                try:
                    for tag in audio.tags:
                        if "APIC" in tag:
                            if audio.tags[tag].type == 3:
                                artwork = Image.open(StringIO(audio.tags[tag].data))
                                break
                            else:
                                artworks.append(audio.tags[tag])
                                artwork_save = True
                        elif "covr" in tag:
                            artwork = Image.open(StringIO(audio.tags[tag][0]))

                    if (not artwork) and artworks and \
                            (artworks[0].mime == 'image/jpeg' or artworks[0].mime == 'image/png'):
                        artwork = Image.open(StringIO(artworks[0].data))

                    if artwork:
                        width, height = artwork.size
                        if width > 400 or height > 400:
                            artwork.thumbnail(artwork_maxsize, Image.ANTIALIAS)
                            artwork_save = True
                            artwork_resize = True
                        elif artwork.format == 'PNG':
                            artwork_save = True

                        if artwork_save:
                            if extension == '.m4a':
                                covr = []
                                covr.append(MP4Cover(artwork.convert('RGB').tostring('jpeg', 'RGB'), MP4Cover.FORMAT_JPEG))
                                audio.tags['covr'] = covr
                                audio.save()
                            else:
                                apic = APIC(
                                    encoding=3,  # utf8
                                    mime="image/jpeg",
                                    type=3,  # front cover
                                    desc=u"Front Cover",
                                    data=artwork.convert('RGB').tostring('jpeg', 'RGB')
                                )

                                # remove old album artworks
                                for tag in audio.tags:
                                    if "APIC" in tag:
                                        del audio.tags[tag]
                                audio.tags.add(apic)
                                audio.save()
                            if artwork_resize:
                                print 'Album artwork resized for file \'{}\' (Original size: {}x{})'.format(file, width, height)
                            else:
                                print 'Sanitized album artwork for file \'{}\''.format(file)

                except Exception as error:
                    print 'Error while writing file details \'{}\':\n {}'.format(file, error)
