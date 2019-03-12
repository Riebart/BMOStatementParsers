#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time


def uuid_format_hash(hash_hex):
    """
    Format a Sha256 hash as UUID's: 8-4-4-4-12
    """
    m = re.match(r"^(.{8})(.{4})(.{4})(.{4})(.{12})", hash_hex)
    return "%s-%s-%s-%s-%s" % (m.group(1), m.group(2), m.group(3), m.group(4),
                               m.group(5))


class StatementParser(object):
    IDENTIFIER_REGEX = None
    LINE_SELECTOR = None
    LINE_TRANSFORM_FROM = None
    LINE_TRANSFORM_TO = None
    FORMAT_FILTER = None
    COLUMN_SEPARATOR = None
    YEAR_TOKEN = None
    SOURCE = None

    @staticmethod
    def statement_date(text):
        return time.localtime()

    @staticmethod
    def process_rows(rows):
        for row in rows:
            row[-1] = float(row[-1].replace("$", "").replace(",", ""))
        return rows

    @staticmethod
    def fix_date(row, year, month, day):
        return row

    @classmethod
    def check(cls, text):
        result = re.search(cls.IDENTIFIER_REGEX, text)
        return result is not None

    @classmethod
    def parse(cls, text):
        stmt_date = cls.statement_date(text)
        lines1 = [l.strip() for l in text.strip().split("\n")]
        lines2 = [l for l in lines1 if re.match(cls.LINE_SELECTOR, l)]

        for l in lines2:
            if not re.search(cls.LINE_TRANSFORM_FROM, l):
                print(l, file=sys.stderr)

        lines3 = [
            re.sub(cls.LINE_TRANSFORM_FROM, cls.LINE_TRANSFORM_TO, l)
            for l in lines2 if re.search(cls.LINE_TRANSFORM_FROM, l)
        ]

        lines4 = [l for l in lines3 if re.match(cls.FORMAT_FILTER, l)]

        rows1 = [[c.strip() for c in l.split(cls.COLUMN_SEPARATOR)]
                 for l in lines4]

        # For each line, replace the year indicator with the year that is appropriate
        # For statements issued in January, make sure that anything from December gets YEAR-1
        rows2 = [
            cls.fix_date(r, stmt_date.tm_year, stmt_date.tm_mon,
                         stmt_date.tm_mday) for r in rows1
        ]

        rows3 = cls.process_rows(rows2)

        return [row + [cls.SOURCE] for row in rows3]


class BMOStandardAccount(StatementParser):
    LINE_SELECTOR = r"^[ 0-9]*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    LINE_TRANSFORM_FROM = r'^([A-Za-z]* [0-9]+) *(?:(Opening balance)|(.*[^ ])(?<!Closing totals) +[^ ]+)  * ([0-9,.$-]+\.[0-9]{2})$'
    LINE_TRANSFORM_TO = r'{{YEAR}} \1|{{YEAR}} \1|\2\3|\4'
    FORMAT_FILTER = r"^[0-9]{4} [A-Z][a-z]{2} [0-9]{1,2}|"
    COLUMN_SEPARATOR = "|"
    YEAR_TOKEN = "{{YEAR}}"
    HEADERS = ["TransactionDate", "PostingDate", "Description", "Amount"]

    @staticmethod
    def fix_date(row, year, month, day):
        for i in [0, 1]:
            row[i] = row[i].lower()
            if month == 1 and "dec" in row[i]:
                row[i] = row[i].replace("{{year}}", str(year - 1))
                row[i] = row[i].replace("dec", "12")
            else:
                row[i] = row[i].replace("{{year}}", str(year))
                month_string = row[i].split(" ")[1]
                row[i] = row[i].replace(
                    month_string,
                    "%02d" % time.strptime(month_string, "%b").tm_mon)

            row[i] = row[i].replace(" ", "-")
        return row

    @staticmethod
    def statement_date(text):
        result = re.search(
            r"For the period ending ([A-Z][a-z]+) ([0-9]+), ([0-9]{4})", text)
        month = result.group(1)
        day = result.group(2)
        year = result.group(3)
        return time.strptime("%s %s %s" % (year, month, day), "%Y %B %d")

    @staticmethod
    def process_rows(rows):
        ret = []
        for i in range(1, len(rows)):
            r0 = rows[i - 1]
            r0[-1] = float(r0[-1].replace("$", "").replace(",", ""))
            r1 = list(rows[i])
            r1[-1] = float(r1[-1].replace("$", "").replace(",", ""))
            r1[-1] -= r0[-1]
            ret.append(r1)
        return ret


class BMOPrimaryChequingAccount(BMOStandardAccount):
    IDENTIFIER_REGEX = "Primary Chequing Account # [0-9]+[0-9 ]*"
    SOURCE = "BMO Chequing Account"


class BMOSavingsBuilderAccount(BMOStandardAccount):
    IDENTIFIER_REGEX = "Savings Builder Account # [0-9]+[0-9 ]*"
    SOURCE = "BMO Savings Account"


class BMOSmartSaverAccount(BMOStandardAccount):
    IDENTIFIER_REGEX = "Smart Saver Account # [0-9]+[0-9 ]*"
    SOURCE = "BMO Savings Account"


class BMOPersonalLineOfCredit(StatementParser):
    IDENTIFIER_REGEX = "YOUR PERSONAL LINE OF CREDIT"
    LINE_SELECTOR = r"^[ 0-9]*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    LINE_TRANSFORM_FROM = r'^[ 0-9]*([A-Za-z]*)\.? +([0-9]+) +([A-Za-z]*)\.? +([0-9]+) +(.*[^ ])     *([0-9,.CR]+) *.*$'
    LINE_TRANSFORM_TO = r'{{YEAR}} \1 \2|{{YEAR}} \3 \4|\5|\6'
    FORMAT_FILTER = r"^[0-9]{4} [A-Z][a-z]{2} [0-9]{1,2}|"
    COLUMN_SEPARATOR = "|"
    YEAR_TOKEN = "{{YEAR}}"
    HEADERS = ["TransactionDate", "PostingDate", "Description", "Amount"]
    SOURCE = "BMO PLOC"

    @staticmethod
    def statement_date(text):
        result = re.search(
            r"Stmt. date: ([A-Z][a-z]{2})\.? ([0-9]+), ([0-9]{4})", text)
        month = result.group(1)
        day = result.group(2)
        year = result.group(3)
        return time.strptime("%s %s %s" % (year, month, day), "%Y %b %d")

    @staticmethod
    def fix_date(row, year, month, day):
        for i in [0, 1]:
            row[i] = row[i].lower()
            if month == 1 and "dec" in row[i]:
                row[i] = row[i].replace("{{year}}", str(year - 1))
                row[i] = row[i].replace("dec", "12")
            else:
                row[i] = row[i].replace("{{year}}", str(year))
                month_string = row[i].split(" ")[1]
                row[i] = row[i].replace(
                    month_string,
                    "%02d" % time.strptime(month_string, "%b").tm_mon)

            row[i] = row[i].replace(" ", "-")
        return row

    @staticmethod
    def process_rows(rows):
        for row in rows:
            val = row[-1].replace("$", "").replace(",", "")
            row[2] = re.sub(r" +", r" ", row[2])
            if "CR" in val:
                row[-1] = -1 * float(val.replace("CR", "").replace(" ", ""))
            else:
                row[-1] = float(val)
        return rows


class BMOWorldMasterCard(StatementParser):
    IDENTIFIER_REGEX = "^ *BMO AIR MILES World (?:Elite)? *Master[Cc]ard"
    LINE_SELECTOR = r"^[ 0-9]*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    LINE_TRANSFORM_FROM = r'([A-Za-z]*)\.? +([0-9]+) +([A-Za-z]*)\.? +([0-9]+) +([^ ].*[^ ]) +(?:(?:[0-9A-Z]{12}|[0-9]{5}[ -][0-9]{6}|[A-Z0-9][0-9]{6} [A-Z]{4}) +| {30} +) ([0-9,]{1,}\.[0-9]{2} ?(CR)?)$'
    LINE_TRANSFORM_TO = r'{{YEAR}} \1 \2|{{YEAR}} \3 \4|\5|\6\7'
    FORMAT_FILTER = r"^[0-9]{4} [A-Z][a-z]{2} [0-9]{1,2}|"
    COLUMN_SEPARATOR = "|"
    YEAR_TOKEN = "{{YEAR}}"
    HEADERS = ["TransactionDate", "PostingDate", "Description", "Amount"]
    SOURCE = "BMO Mastercard"

    @staticmethod
    def statement_date(text):
        result = re.search(
            r"New Balance, ([A-Z][a-z]{2})\.? ([0-9]+), ([0-9]{4})", text)
        month = result.group(1)
        day = result.group(2)
        year = result.group(3)
        return time.strptime("%s %s %s" % (year, month, day), "%Y %b %d")

    @staticmethod
    def process_rows(rows):
        for row in rows:
            val = row[-1].replace("$", "").replace(",", "")
            row[2] = re.sub(r" +", r" ", row[2])
            if "CR" in val:
                row[-1] = -1 * float(val.replace("CR", "").replace(" ", ""))
            else:
                row[-1] = float(val)
        return rows

    @staticmethod
    def fix_date(row, year, month, day):
        for i in [0, 1]:
            row[i] = row[i].lower()
            if month == 1 and "dec" in row[i]:
                row[i] = row[i].replace("{{year}}", str(year - 1))
                row[i] = row[i].replace("dec", "12")
            else:
                row[i] = row[i].replace("{{year}}", str(year))
                month_string = row[i].split(" ")[1]
                row[i] = row[i].replace(
                    month_string,
                    "%02d" % time.strptime(month_string, "%b").tm_mon)

            row[i] = row[i].replace(" ", "-")
        return row


PARSERS = [
    BMOPrimaryChequingAccount, BMOSavingsBuilderAccount, BMOSmartSaverAccount,
    BMOPersonalLineOfCredit, BMOWorldMasterCard
]


def main():
    parser = argparse.ArgumentParser(
        description=
        """Parse a supported PDF input file into a CSV of transactions.""")
    parser.add_argument(
        "--file", help="""PDF file to parse""", required=True, default=None)
    parser.add_argument(
        "--id",
        help="""Add identifiers to each row as the first column""",
        action="store_true",
        default=False)
    parsed_args = parser.parse_args()

    with open(parsed_args.file, "rb") as fp:
        pdf = fp.read()

    proc = subprocess.Popen(("pdftotext", "-layout", "-", "-"),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    proc.stdin.write(pdf)
    stdout, _ = proc.communicate()
    text = stdout.decode("utf-8")

    for parser in PARSERS:
        if parser.check(text):
            rows = parser.parse(text)
            w = csv.writer(sys.stdout)
            w.writerow((["Id"] if parsed_args.id else []) + parser.HEADERS +
                       ["RecordSource"])
            for row in rows:
                if parsed_args.id:
                    row = [
                        uuid_format_hash(
                            hashlib.sha256(
                                str(row).encode("utf-8")).hexdigest())
                    ] + row
                w.writerow(row)


if __name__ == "__main__":
    main()
