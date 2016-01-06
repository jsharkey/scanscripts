
# Simple wrapper for SANE
# Usage: scan.sh [printer] [year] [prefix] [index]


if [ $1 = "new" ]; then
    PRINTER=192.168.1.23
else
    PRINTER=192.168.1.11
fi

YEAR=$2
TITLE=$3
START=$4

scanimage \
    -d epson2:net:$PRINTER \
    --mode Color \
    --resolution 300 \
    --format=tiff \
    --batch=$YEAR-$TITLE-%04d.tif --batch-start=$START --batch-count=500 --batch-prompt -p

#     --compression=JPEG \
#    --jpeg-quality=95 \


# nice printer
# 300dpi 20s
# 600dpi 75s

# cheap printer
# 300dpi 37s
# 600dpi 113s


#22:12
#23:59
#60+48=108 mins, 186 scans
#186/108=   1.7 scans/min
#2.75+1.5+3.125 = 7.375in
# 4.09722222 inches per hour

# (25MB*186)/7.375"

# 630.508475 MB per inch
# 9+11.5+10+7.5=38
# 23.959GB
