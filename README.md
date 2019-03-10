# BMO Statement Parsers

A Python script that contains regular expression matchers and parsers to convert PDF eStatements from Bank of Montreal into usable CSVs.

## Supported Statement Types

- Primary Chequing Account (`BMOStandardAccount`)
- Savings Builder Account (`BMOStandardAccount`)
- Personal Line of Credit (`BMOPersonalLineOfCredit`)
- BMO World Elite MasterCard (`BMOWorldMasterCard`)

The parsers are somewhat generic, and should work with little or no modification to handle many similar variants. For example, the `BMOWorldMasterCard` parser should handle, with an obvious extension to the `IDENTIFIER_REGEX`, any BMO MasterCard variant.

Similarly, the `BMOStandardAccount` parser should handle most standard BMO chequing and savings accounts, likely including business accounts.

**Only the above listed account types have been tested with the parsers.**
