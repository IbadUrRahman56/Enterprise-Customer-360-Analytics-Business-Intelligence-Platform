import argparse
from pathlib import Path
from .config import DATA, OUTPUT


def main():
    parser=argparse.ArgumentParser(description="Customer 360 pipeline and reporting")
    subs=parser.add_subparsers(dest="command",required=True)
    demo=subs.add_parser("demo"); demo.add_argument("--customers",type=int,default=1800); demo.add_argument("--orders",type=int,default=36000)
    demo.add_argument("--seed",type=int,default=42); demo.add_argument("--data-dir",type=Path,default=DATA)
    ingest=subs.add_parser("ingest"); ingest.add_argument("source",type=Path); ingest.add_argument("--data-dir",type=Path,default=DATA)
    reports=subs.add_parser("report"); reports.add_argument("--cadence",choices=["weekly","monthly","quarterly","all"],default="all"); reports.add_argument("--as-of"); reports.add_argument("--warehouse",type=Path,default=DATA/"warehouse.duckdb"); reports.add_argument("--output",type=Path,default=OUTPUT/"reports")
    subs.add_parser("password-hash")
    args=parser.parse_args()
    if args.command=="demo":
        if args.customers<10 or args.orders<100: parser.error("Use at least 10 customers and 100 orders")
        from .demo import generate
        from .pipeline import build
        source=args.data_dir/"raw"
        generate(source,args.customers,args.orders,args.seed)
        result=build(source,args.data_dir)
        print(f"Demo ready. Run {result['run_id']}; {args.data_dir/'warehouse.duckdb'}")
    elif args.command=="ingest":
        from .pipeline import build
        result=build(args.source,args.data_dir); print(f"Built run {result['run_id']}")
    elif args.command=="report":
        from .reports import generate_reports
        for path in generate_reports(args.warehouse,args.output,args.cadence,args.as_of): print(path)
    else:
        from getpass import getpass
        from .security import hash_password
        print(hash_password(getpass("Password: ")))


if __name__=="__main__": main()
