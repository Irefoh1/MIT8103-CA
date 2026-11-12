# Read and explain the catalogue queries

Connect using the command in the README, then select the lab database:

```javascript
use markethub_p4
```

**Read a product by SKU:**

```javascript
db.products.findOne({sku: 'KB-001'})
```

This returns the product, embedded category, and its attributes together.

**Browse active electronics in price order:**

```javascript
db.products.find({'category.name':'Electronics', active:true})
  .sort({price:1, sku:1})
```

Dot notation reaches inside the category object. `1` means ascending order.

**Filter by price:**

```javascript
db.products.find({price:{$gte:Decimal128('2000'), $lte:Decimal128('5000')}})
  .sort({price:1})
```

`$gte` and `$lte` mean greater-than-or-equal and less-than-or-equal. Decimal128 keeps the comparison in decimal money values. The seed produces notebook and mouse.

**Search attributes and tags:**

```javascript
db.products.find({'attributes.connection':'USB', tags:'computer'})
```

The tag condition matches an element of the tags array; no string-splitting is needed. A notebook document need not have a connection field and will not match.

**Summarise catalogue prices:**

```javascript
db.products.aggregate([
  {$group:{_id:'$category.name', product_count:{$sum:1}, average_price:{$avg:'$price'}}},
  {$sort:{_id:1}}
])
```

This groups products by embedded category name. For the original snapshot, electronics has two products and an average price of NGN 10,000. It is a catalogue-price summary, not order revenue.

**Update nested attributes:**

```javascript
db.products.updateOne({sku:'KB-001'}, {$set:{'attributes.backlit':true}})
```

This changes one keyboard field without replacing its entire document. The automated lab already performs this update plus adding cable length; repeating it can report zero modified documents because the value is already true.

**Inspect an actual plan:**

```javascript
db.products.find({sku:'KB-001'}).explain('executionStats')
db.products.getIndexes()
```

Inspect the winning plan's index name, returned rows, and documents examined. MongoDB can display different stage shapes between server versions; this lab checks the selected index name rather than assuming a particular stage label.

The complete insertion, validation failures, and temporary-document deletion are in `catalogue-lab.js`. Do not rerun that full script against the already populated database: it deliberately refuses reuse. Interactive writes change the final lab state; the saved evidence remains a record of the original run.
