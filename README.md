# BMO Statement Parsers

A Python script that contains regular expression matchers and parsers to convert PDF eStatements from Bank of Montreal into usable CSVs.

## Using it

You'll need `pdftotext`, which comes in `poppler-utils` on Ubuntu, in your PATH, and python3, as well as your PDF eStatements from BMO, which you can get from online banking. Then it is as simple as:

`python3 parse.py --file eStatement_2018-01-01.pdf > out.csv`

Open the CSV in your favourite spreadsheet program, or continue to process as you like.

## Why PDF eStatements

Simply put, PDF eStatements are available from the beginning of your account history for all accounts, including PLOCs, TFSAs, bank accounts, and credit cards.

Account transaction history is available for 90 days for credit cards and 24 months for other accounts, but is only viewable online. Downloading account details only contain 90 days at a time.

## Supported Statement Types

- Primary Chequing Account (`BMOStandardAccount`)
- Savings Builder Account (`BMOStandardAccount`)
- Smart Saver Account (`BMOStandardAccount`)
- Personal Line of Credit (`BMOPersonalLineOfCredit`)
- BMO World Elite MasterCard (`BMOWorldMasterCard`)
  - Statements for MasterCard products from BMO prior to 2014-05 used a different layout not supported by this parser class.

The parsers are somewhat generic, and should work with little or no modification to handle many similar variants. For example, the `BMOWorldMasterCard` parser should handle, with an obvious extension to the `IDENTIFIER_REGEX`, any BMO MasterCard variant.

Similarly, the `BMOStandardAccount` parser should handle most standard BMO chequing and savings accounts, likely including business accounts.

**Only the above listed account types have been tested with the parsers.**
