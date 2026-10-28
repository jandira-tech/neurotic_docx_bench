"""Finish v1, then build/validate/clean the two Wordcraft phases sequentially.

Starts only when the full v1 case file exists (not a sample). The split run is deliberately
not substituted: its exact candidate inputs must be supplied first.
"""
import time
from pathlib import Path
import finish_set
import fetch_wordcraft
import prepare
import process
import report
import patch_site


def main():
    while not (process.BUILD/'cases_v1.json').is_file():
        time.sleep(5)
    print('STAGE: validate and clean v1',flush=True)
    finish_set.main(['v1'])
    for phase in ['compare','convert']:
        which='wordcraft_'+phase
        print('STAGE: '+which+' download',flush=True)
        prepare.wordcraft(phase)
        fetch_wordcraft.main(['pdfs',phase])
        print('STAGE: '+which+' score and encode',flush=True)
        process.main([which])
        finish_set.main([which])
    report.main(['--allow-partial'])
    patch_site.main(['--allow-partial'])
    print('STAGE: completed v1 and Wordcraft; split source gap remains',flush=True)

if __name__=='__main__':main()
