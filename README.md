What does it do?
----------------

Simplify your USaver and Ultra account statements into a single statement.


What problem does it address?
-----------------------------

[UBank](https://www.ubank.com.au), an online bank in Australia, offers
a product called "USaver Ultra" which is a high interest savings account
paired with a transaction account. It's easy to operate, because the
transaction account is *automatically* topped up from the saving account.
But it's painful to read the account statements, because the automatic
top-up (or "sweep") transactions outnumber the real transactions.

It's particularly frustrating if you want to record your personal
finances, and reconcile them against your bank statements.


What's the solution?
--------------------

You really don't care which of the two accounts your money is in. You
just want to know what goes in and what comes out. Conceptually, you
treat your "USaver Ultra" as a single account. And by using this program,
you can combine your online transaction statements for the "USaver" and
"Ultra" accounts into a single statement. By omitting the movement of
funds between the two accounts (both automatic "sweeps" or manual
transfers), you can concentrate on what's important: deposits and
withdrawals.


How do I use it?
----------------

In its current form, using the program demands some tech savvy.
(If there is enough demand, I will consider producing an more
user-friendly online version).

In order to run the program, you need to have Python installed on your
computer (Mac and Linux users, you already have it). It's been tested
against Python 2.7, but earlier versions will probably work. It is not
compatible with Python 3.

Log onto UBank, and separately export the transaction history for both
the USaver and Ultra accounts in CSV format. Then just run the program,
passing it the names of the CSV files, e.g.:

    ./usaverultra.py 33036_11_21_2014.csv 55446_11_21_2014.csv

The output format should be self-explanatory.

