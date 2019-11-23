pip-compile::
	pip install -U pip-tools
	pip-compile requirements.in

pip-compile-dev::
	pip install -U pip-tools
	pip-compile --upgrade requirements-dev.in

install:: pip-compile pip-compile-dev
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install -e .

build: clean
	pip install wheel
	python setup.py sdist bdist_wheel

languages = de fr en
make_messages:
	$(foreach lang, $(languages), ./make_messages.py $(lang);)

compile_messages:
	./compile_messages.py all
