import os
import re
import zlib
import importlib

import pyminifier.token_utils
import pyminifier.minification


def do(path, config):
    with open(path, 'r') as f:
        name = os.path.basename(path)

        original = f.read()

        for k, v in config.items():
            original = original.replace(k, v)

        class Bunch:
            def __init__(self, **kwds):
                self.__dict__.update(kwds)

        minified = pyminifier.minification.minify(pyminifier.token_utils.listified_tokenizer(original), Bunch(tabs=False))

        # print(minified)

        print('# Original: {} Minified: {} Saved: {}'.format(len(original), len(minified), len(original) - len(minified)))
        # print('import esp')
        # print('import machine')
        # print('esp.osdebug(None)')
        # print('machine.freq(160000000)')
        print('gc.collect()')
        print('f = open("{}", "w")'.format(name))

        for part in re.findall('.{1,1000}', minified, re.DOTALL):
            # print('f.write(d({!r}))'.format(zlib.compress(part.encode('ascii'), 9)))
            print('f.write({!r})'.format(part))

        print('f.close()')
        # print('machine.reset()')


def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('files', nargs='+')
    parser.add_argument('--config', nargs='*', default=[])

    args = parser.parse_args()

    config = {}
    for file in args.config:
        config.update({k: v for k, v in vars(importlib.import_module(file)).items() if not k.startswith('__')})
    for file in args.files:
        do(file, config)

if __name__ == '__main__':
    main()
