# Very simple Makefile
#  by Franz Kirsten

# modify as you see fit, make sure INSTALLDIR is in your PATH variable
INSTALLDIR = /usr/local/bin

install:
	cp base2fil.sh $(INSTALLDIR)/base2fil ; chmod u+x,g+x,o+x $(INSTALLDIR)/base2fil
	cp setfifo.perl $(INSTALLDIR)/setfifo ; chmod u+x,g+x,o+x $(INSTALLDIR)/setfifo 
	cp process_vdif.py $(INSTALLDIR)/process_vdif ; chmod u+x,g+x,o+x $(INSTALLDIR)/process_vdif
	cp cmd2flexbuff.py $(INSTALLDIR)/cmd2flexbuff ; chmod u+x,g+x,o+x $(INSTALLDIR)/cmd2flexbuff
	cp spif2file.sh $(INSTALLDIR)/spif2file ; chmod u+x,g+x,o+x $(INSTALLDIR)/spif2file
	cp create_config.py $(INSTALLDIR)/create_config.py ;  chmod u+x,g+x,o+x $(INSTALLDIR)/create_config.py
	cp obsinfo.py $(INSTALLDIR)/obsinfo.py ;  chmod u+x,g+x,o+x $(INSTALLDIR)/obsinfo.py

clean:
	rm -f $(INSTALLDIR)/base2fil
	rm -f $(INSTALLDIR)/setfifo
	rm -f $(INSTALLDIR)/process_vdif
	rm -f $(INSTALLDIR)/cmd2flexbuff
	rm -f $(INSTALLDIR)/spif2file
	rm -f $(INSTALLDIR)/create_config.py
	rm -f $(INSTALLDIR)/obsinfo.py
