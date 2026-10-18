# Understand and make genuine contributions

This is a learning workbook, not a similarity-detector evasion guide. The goal is to understand and improve the project with accurate attribution. Changing variable names, colours or file formatting does not establish independent authorship.

## Explain one complete booking

Choose a booking ID from a genuine run. Locate its Reservation record and state steps, its Inventory hold, its Payment record and its Notification record. Use each database's own diagnostic login. Explain why services themselves only use APIs. Identify the correlation ID linking the request logs.

Questions to answer in your own words:

1. Which service decides the room price, and why does the client not submit a charge amount?
2. Where does stock decrease, and what makes that update atomic?
3. What would go wrong with SELECT-then-UPDATE outside a proper transaction/lock?
4. How are simultaneous first requests with the same key serialized?
5. How do unique booking IDs help when callers accidentally use different keys?
6. Why are effect and cached response committed together?
7. Why does Reservation store its state between HTTP calls?
8. Why does a payment timeout retain the room rather than immediately cancel?
9. Why does a 202 POST replay stay 202 after a GET shows CONFIRMED?
10. Why is notification failure different from payment decline?
11. Why must a successful payment be refunded before releasing its room?
12. How does a stopped service recover without creating a second charge?

## Follow the implementation

| Area | Read | Find the proof |
|---|---|---|
| Inventory | main.py, rules.py, repository.py, database/schema.sql | available > 0 update, rowcount decision, hold uniqueness |
| Reservation | main.py, repository.py, saga.py, rules.py | durable claim, state transitions, stable downstream keys, recovery lock |
| PHP Payment | src/main.php, rules.php, repository.php, platform.php | integer amounts, declared mock modes, one charge/refund, transaction/cache |
| PHP Notification | corresponding PHP files | confirmed-state check, failed-first-attempt, retry of same record |
| Optional UI | ui/bootstrap.php, public/api.php, assets/app.js | fixed API gateway actions, no database credentials, original POST versus current GET |

## Choose genuine work you can defend

Each member can own a service review, reproduce a failure, add a meaningful missing test, fix a verified bug, or improve the corresponding explanation from observed behavior. Write down the problem, your reasoning, exact changed files, tests run and limitations. Use your own account/identity to commit that real work. Add another business feature only if you can justify it within the assignment's scope and maintain all existing invariants.

Examples of useful investigation: test capacity one; vary concurrent callers; check Unicode payload replay; verify wrong-password denial; interrupt a service during a slow payment; compare original POST and recovered GET. Capture actual outcomes. If a test reveals a bug, fix it and rerun the affected checks.

## Prepare your reflection

Write approximately half a page in your own voice: what you personally did, the hardest problem you actually solved, evidence that changed your understanding, and what you would improve. Include true AI assistance. Use the individual template, not an invented first-person story supplied by someone else.

## Useful viva answers to practise

- Explain the difference between a database transaction and a distributed saga.
- Explain why a database-per-service pattern can use one local server with separate databases/accounts.
- Explain a named session lock versus a row lock and a UNIQUE constraint.
- Explain READ COMMITTED in the particular key-lock/query sequence.
- Explain why an idempotency key alone is insufficient without a payload fingerprint.
- Explain why a green health check does not prove the entire booking workflow.
- Explain one design alternative and why you rejected it.

Practise with code and real evidence open. The institution evaluates understanding and individual contribution, not how closely you can repeat a generated paragraph.
