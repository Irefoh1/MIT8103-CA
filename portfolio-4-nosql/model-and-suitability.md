# MarketHub document model and suitability

## Why model a product catalogue?

A shopper often needs one product's name, price, category, tags, and specifications together. Keyboards have layouts and connection types; notebooks have paper sizes and page counts. A document can group these facts while allowing different product-specific fields. This is a deliberate extension of the same retailer's catalogue, not a replacement organisation or a conversion of all SQL tables.

MongoDB is used for document modelling in this activity. PostgreSQL remains the authoritative store for the transactional order, payment, and inventory examples developed earlier. P4's MongoDB data is a **point-in-time read-only export followed by local catalogue demonstrations**, not an automatically synchronised production service.

## Document example

Readable mongosh-style structure; actual source IDs and timestamps are recorded in evidence:

```javascript
{
  _id: ObjectId('...'),               // MongoDB identity
  product_id: Long('1'),              // original PostgreSQL identity
  sku: 'KB-001',
  name: 'USB Keyboard',
  description: null,
  category: {category_id: Long('1'), name: 'Electronics'},
  price: Decimal128('15000.00'),
  currency: 'NGN',
  active: true,
  attributes: {layout: 'QWERTY', connection: 'USB', backlit: false},
  tags: ['computer', 'accessory'],
  source: {
    system: 'PostgreSQL P1 snapshot',
    imported_at: ISODate('...')
  }
}
```

The ellipses indicate illustrative placeholders, not executable BSON values. See `evidence/01-imported-documents.ejson` for complete real documents. The local update changes backlit to true and adds cable length; the final export records that difference.

## SQL-to-document mapping

| PostgreSQL fact | MongoDB representation | Reason |
|---|---|---|
| products.product_id | product_id, BSON Long, unique | Stable mapping to the original SQL product; avoid JavaScript large-integer precision loss |
| products.sku | sku, unique | Product lookup and business identity |
| products.product_name | name | Display name |
| products.description | description, string or null | Preserve the source's optional description |
| products.current_price | price, Decimal128 | Exact decimal NGN catalogue price |
| products.is_active | active, Boolean | Catalogue availability flag, not live stock availability |
| categories.category_id/category_name | Embedded category object | Retrieve product and category display together |
| New fictional product specifications | attributes object | Different fields for keyboards, mice, and notebooks |
| New fictional search labels | tags array | Multiple labels without comma-separated strings |
| Export provenance | source object with timestamp | Identify source system and import moment |

Stock quantity is deliberately absent. Product activity does not establish available stock. Orders still preserve historical purchase prices and delivery addresses in PostgreSQL as designed in P1.

## Embedding and references

Category ID and name are embedded in each product, avoiding a join or a separate category lookup for a product listing. This repeats a category name across products. Renaming a category therefore requires updating all affected embedded copies or rebuilding the snapshot; failing to do so can create inconsistent displays.

The source category ID supports mapping, but MongoDB does not enforce a foreign key back to PostgreSQL. Two unique indexes enforce catalogue-wide uniqueness of product_id and sku inside this MongoDB collection only. They do not validate that the referenced source record still exists.

Attributes are embedded because they belong to a product and are normally retrieved with it. A separate document per attribute would complicate this small read pattern. A growing unbounded list of orders or reviews is not embedded in products; such lists would need their own modelling decisions.

## Validation and indexes

The collection uses strict/error JSON Schema validation. Required common fields have BSON types; empty/whitespace-only names and SKUs are rejected, price must be nonnegative Decimal128, currency must be NGN, and tags must be distinct nonblank strings. Top-level extra fields and extra category/provenance fields are rejected. Long IDs must be positive.

Attributes permit different nested fields, but no category-specific schema is imposed. For example, this validator does not ensure a notebook page count is positive or that connection is one of a fixed list. That is a limitation and a possible future validation extension, not proof that flexible documents are inherently unvalidated.

Indexes:

- MongoDB's default unique `_id` index identifies each document.
- Unique `sku` supports lookup and rejects duplicate business identifiers.
- Unique `product_id` preserves one document per source product.
- Compound `category.name, active, price` supports the intended category/active/price browsing pattern. With only three products, the optimiser may reasonably choose a collection scan for some filters. No forced hint or fabricated speedup is used.

The executed SKU plan establishes actual index use and one examined document. Indexes add storage and maintenance costs; tiny-data lookup evidence does not measure production scalability.

## Suitability compared with other models

| Model | Potential MarketHub use | Why selected/not selected here |
|---|---|---|
| Document | Product catalogue with varying attributes | Implemented: grouped product reads and nested fields fit the exercise |
| Relational | Stock, orders, payments | Already implemented; keys, constraints, joins, and transactions suit those workflows |
| Key-value | Cached catalogue response or shopping session | Useful for direct key retrieval; not implemented and not needed for this document query demonstration |
| Graph | Product recommendations and related-product paths | Useful when relationships dominate; not implemented for this small catalogue |
| Wide-column | Large-scale event/activity access patterns | Would need a workload-driven partition design; not implemented |

PostgreSQL could also represent flexible attributes using an appropriate schema or JSONB. Choosing MongoDB here demonstrates an alternative data model; it is not evidence that SQL cannot handle catalogue data or that MongoDB is always faster.

## Synchronisation, consistency, and boundaries

The runner reads the three P1 records in one SQL query, saves the export, and constructs documents with reviewed fictional enrichments. There is no change-data-capture pipeline, scheduled refresh, bidirectional update, or cross-database transaction. After import, prices and active flags can become stale. Local MongoDB edits do not affect SQL.

A future system could refresh snapshots or implement an event/CDC pipeline, retaining stable IDs, processing deletions, and handling retries/version ordering. Embedded category changes would also need propagation. Those mechanisms are proposed, not implemented.

Catalogue browsing may tolerate explicitly bounded staleness; checkout stock and payment decisions must continue using the authoritative transactional store. The MongoDB server is standalone, with no replica set, sharding, automatic failover, or multi-document transaction demonstration. Portfolio 5 will address distributed concepts separately. A single-document update is demonstrated; no claim of atomic updates across SQL and MongoDB is made.
