# Portfolio 4: NoSQL and Advanced Data Models

## Objective and case study

Implement a **MongoDB document catalogue** for MarketHub, the same e-commerce retailer used in Portfolios 1–3. Demonstrate a NoSQL model, working inserts/reads/updates/deletes, validation, indexing, and an explanation of suitability. The brief permits a document, key-value, column, or graph example; this activity implements the document option.

The three source products are the P1 USB keyboard (`KB-001`), optical mouse (`MS-001`), and notebook (`NB-001`). The runner exports their actual IDs, categories, names, prices, descriptions, and active flags from the existing PostgreSQL P1 database. Added attributes/tags are explicitly fictional catalogue enrichments, not facts inferred from SQL. Earlier portfolio files and database data are not modified.

## Deliverables

| File | Purpose |
|---|---|
| [model-and-suitability.md](model-and-suitability.md) | Document structure, SQL mapping, embedding, consistency, and model tradeoffs |
| [catalogue-lab.js](catalogue-lab.js) | Executable mongosh collection, validator, indexes, CRUD, aggregation, and checks |
| [run-lab.py](run-lab.py) | Reproducible read-only SQL export and isolated Docker lab |
| [query-walkthrough.md](query-walkthrough.md) | Short, understandable queries for personal review |
| [evidence/](evidence/) | Real source snapshot, BSON-preserving outputs, errors, plans, index definitions, and environment |

## Run the lab

Prerequisites: Python 3, Docker CLI/engine, original P1 PostgreSQL database, and the official MongoDB image. No third-party Python package is required. From the repository root:

```powershell
docker pull mongo:8.0
python portfolio-4-nosql/run-lab.py
```

Defaults: PostgreSQL container `markethub-p1-validation`, source database `markethub_portfolio`, new MongoDB container `markethub-p4-mongo`, target database `markethub_p4`. The container has no network access, published host ports, or host-directory mounts. mongosh executes inside it through Docker. Authentication is not configured for this isolated lab; this is not a production deployment.

The runner refuses an existing container name. The JavaScript refuses a nonempty target database. It never drops an existing database or collection. For a second run:

```powershell
python portfolio-4-nosql/run-lab.py --mongo-container markethub-p4-repeat --database markethub_p4_repeat
```

Use `--postgres-container` and `--postgres-database` if the P1 source has another location. Keep the original three source SKUs available. A repeat replaces local evidence files, so preserve old results first if needed. To inspect the completed default lab:

```powershell
docker exec -it markethub-p4-mongo mongosh markethub_p4
```

The image tag can change over time; the actual image ID/digest, server and shell versions are recorded in the evidence so the verified environment is identifiable. MongoDB database files stay in Docker-managed storage, not in GitHub.

## What the implementation demonstrates

1. Import three products, using BSON Long for source IDs and Decimal128 for money.
2. Read active electronics using an embedded category field.
3. Find notebook/mouse using an inclusive NGN 2,000–5,000 price range.
4. Filter nested attributes and tags to find USB computer accessories.
5. Aggregate products by category and calculate average catalogue price, not sales revenue.
6. Update keyboard attributes without requiring notebook documents to have keyboard fields.
7. Insert and delete a temporary lab product, preserving all three imported records.
8. Reject duplicate SKU/ID, negative or binary-floating-point price, wrong currency, blank name, and non-object attributes.
9. Inspect the SKU query's actual execution plan and verify use of its unique index.

All modifications occur only in MongoDB's separate snapshot. The keyboard's backlight update is a local lab demonstration; it is not written back to PostgreSQL. Category attributes are flexible objects, while common product fields have a strict schema. That does not mean every possible attribute value is validated.

## Evidence format and scope

**Verified result:** On 12 November 2026 (Africa/Lagos), all **19 checks passed** using MongoDB **8.0.38** and mongosh **2.14.2**. The SKU lookup selected `sku_unique` (`EXPRESS_IXSCAN`), returned one record, and examined one document. Seven invalid writes were rejected with the expected duplicate-key or validation codes. The final catalogue contains the original three products. See [check summary](evidence/verification.txt), [execution log](evidence/execution.txt), and [server environment](evidence/environment.ejson).

`.ejson` files use canonical MongoDB Extended JSON, preserving types such as `$numberLong`, `$numberDecimal`, `$date`, and `$oid`. They are readable technical outputs, not plain JSON import files with all BSON typing removed. `postgresql-source-snapshot.json` is the actual SQL export; `source-query.sql` records how it was obtained.

The execution and check summaries show real MongoDB operations. Index and collection-options files preserve the actual definitions; the SKU execution plan records examined documents and returned rows. Three documents are sufficient to demonstrate the model and index access, but do not establish performance benefits at scale. There is no timing-speedup claim.

## Source and AI-use record

Case-study source: the existing MarketHub P1 schema and seed data. Assessment source: MIT 8103 assignment brief, Portfolio 4 expected evidence (NoSQL model using the same case study, implementation evidence, and suitability explanation).

OpenAI Codex assisted with the model, code, documentation, and initial lab execution. The student must record personal review, corrections, testing, and understanding honestly in the final AI-use declaration. The supplied analysis is not a personal reflection written on the student's behalf.
