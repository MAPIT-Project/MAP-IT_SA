cd ..
#do tests
python -m unittest discover ..
#do docs
doxygen -g doxy-config-file.cfg

