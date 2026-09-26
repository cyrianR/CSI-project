all: js

OUTPUT=js/obja.js

js: src/*
	rm -f ${OUTPUT}
	cat src/Loader.js >> ${OUTPUT} && echo >> ${OUTPUT}
	cat src/Model.js >> ${OUTPUT} && echo >> ${OUTPUT}

