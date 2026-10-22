"""CPU dispatcher for the explicitly requested complete augmentation workflow."""
import argparse
import fcntl
import json
from pathlib import Path

from somaforge_core.augmentation_refinement import read_config, run, candidate
from somaforge_core.trajectory_refinement import resolve, somaforge_root


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--stage',choices=['prepare','generate','references','train','evaluate','collect','export','all','status','candidate'],default='prepare')
    parser.add_argument('--identity',help='Internal isolated candidate identity; used by the parallel controller')
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.stage=='candidate':
        if not args.execute or not args.identity:parser.error('candidate requires --execute and --identity')
        print(json.dumps(candidate(args.config,args.identity)))
        return
    if args.execute:
        config=read_config(args.config)
        output=resolve(config['refinement']['output_dir'],somaforge_root());output.mkdir(parents=True,exist_ok=True)
        with (output/'augmentation_controller.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result=run(args.config,args.stage,execute=True)
    else:result=run(args.config,args.stage,execute=False)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
