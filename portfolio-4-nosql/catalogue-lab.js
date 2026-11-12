// Run with mongosh through run-lab.py. No database or collection is dropped.
const fs = require('fs');
const databaseName = process.env.P4_DATABASE || 'markethub_p4';
const out = '/tmp/p4-output';
fs.mkdirSync(out, {recursive:true});
const lab = db.getSiblingDB(databaseName);
if (lab.getCollectionNames().length !== 0) {
  throw new Error('Refusing to reuse a nonempty database: '+databaseName);
}
const checks = [];
function verify(condition, message) {
  if (!condition) throw new Error('FAIL: '+message);
  checks.push('PASS: '+message);
  print(checks[checks.length-1]);
}
function save(name,value) {
  fs.writeFileSync(out+'/'+name,EJSON.stringify(value,null,2,{relaxed:false})+'\n');
}
lab.createCollection('products', {
  validationLevel:'strict', validationAction:'error',
  validator: {$jsonSchema: {
    bsonType:'object', additionalProperties:false,
    required:['_id','product_id','sku','name','description','category','price',
      'currency','active','attributes','tags','source'],
    properties: {
      _id:{bsonType:'objectId'},
      product_id:{bsonType:'long',minimum:Long('1')},
      sku:{bsonType:'string',pattern:'\\S'},
      name:{bsonType:'string',pattern:'\\S'},
      description:{bsonType:['string','null']},
      category:{bsonType:'object',additionalProperties:false,required:['category_id','name'],
        properties:{category_id:{bsonType:'long',minimum:Long('1')},name:{bsonType:'string',pattern:'\\S'}}},
      price:{bsonType:'decimal',minimum:Decimal128('0')},
      currency:{enum:['NGN']}, active:{bsonType:'bool'},
      // Deliberately flexible: type-specific attributes live inside this object.
      attributes:{bsonType:'object'},
      tags:{bsonType:'array',uniqueItems:true,items:{bsonType:'string',pattern:'\\S'}},
      source:{bsonType:'object',additionalProperties:false,required:['system','imported_at'],
        properties:{system:{enum:['PostgreSQL P1 snapshot']},imported_at:{bsonType:'date'}}}
    }
  }}
});
const products=lab.products;
products.createIndex({sku:1},{unique:true,name:'sku_unique'});
products.createIndex({product_id:1},{unique:true,name:'product_id_unique'});
products.createIndex({'category.name':1,active:1,price:1},{name:'category_active_price'});
const source=JSON.parse(fs.readFileSync('/tmp/p4-source.json','utf8'));
const enrichments={
 'KB-001':{attributes:{layout:'QWERTY',connection:'USB',backlit:false},tags:['computer','accessory']},
 'MS-001':{attributes:{connection:'USB',dpi:Int32(1600),buttons:Int32(3)},tags:['computer','accessory']},
 'NB-001':{attributes:{paper_size:'A5',pages:Int32(120),ruling:'lined'},tags:['stationery','paper']}
};
const importedAt=new Date();
const docs=source.map(p=>{
  if (!enrichments[p.sku]) throw new Error('No reviewed enrichment for SKU '+p.sku);
  return {_id:new ObjectId(),product_id:Long(p.product_id),sku:p.sku,name:p.name,
    description:p.description,category:{category_id:Long(p.category_id),name:p.category_name},
    price:Decimal128(p.price),currency:'NGN',active:p.active,
    ...enrichments[p.sku],source:{system:'PostgreSQL P1 snapshot',imported_at:importedAt}};
});
products.insertMany(docs);
verify(products.countDocuments({})===3,'Imported three P1 products as BSON documents');
verify(docs.every(d=>products.findOne({sku:d.sku}).price.toString()===d.price.toString()),
       'All imported prices equal the PostgreSQL snapshot using Decimal128');
save('01-imported-documents.ejson',products.find().sort({sku:1}).toArray());
save('02-electronics.ejson',products.find({'category.name':'Electronics',active:true}).sort({price:1,sku:1}).toArray());
verify(products.countDocuments({'category.name':'Electronics',active:true})===2,'Embedded category filter returns two electronics products');
save('03-price-range.ejson',products.find({price:{$gte:Decimal128('2000'),$lte:Decimal128('5000')}}).sort({price:1}).toArray());
verify(products.countDocuments({price:{$gte:Decimal128('2000'),$lte:Decimal128('5000')}})===2,'Decimal price-range query returns notebook and mouse');
save('04-attributes-and-tags.ejson',products.find({'attributes.connection':'USB',tags:'computer'}).sort({sku:1}).toArray());
verify(products.countDocuments({'attributes.connection':'USB',tags:'computer'})===2,'Nested attributes and array membership identify USB accessories');
const grouped=products.aggregate([
 {$group:{_id:'$category.name',product_count:{$sum:1},average_price:{$avg:'$price'}}},
 {$sort:{_id:1}}
]).toArray();
save('05-category-aggregation.ejson',grouped);
verify(grouped.length===2 && grouped[0]._id==='Electronics' && grouped[0].average_price.toString()==='10000.00',
       'Aggregation computes two categories and NGN 10000.00 electronics average');
const update=products.updateOne({sku:'KB-001'},{$set:{'attributes.backlit':true,'attributes.cable_length_m':Decimal128('1.5')}});
verify(update.modifiedCount===1 && products.findOne({sku:'KB-001'}).attributes.backlit===true,
       'Updated keyboard attributes without changing other product shapes');
save('06-updated-keyboard.ejson',products.findOne({sku:'KB-001'}));

// Demonstrate delete with a clearly marked temporary lab document only.
const temporary={...docs[0],_id:new ObjectId(),product_id:Long('9000001'),sku:'TEMP-P4',name:'Temporary lab product'};
products.insertOne(temporary);
verify(products.countDocuments({sku:'TEMP-P4'})===1,'Inserted temporary document for delete demonstration');
verify(products.deleteOne({sku:'TEMP-P4'}).deletedCount===1 && products.countDocuments({})===3,
       'Deleted temporary document while preserving the three source products');

const errors=[];
function rejected(label,change,expectedCode) {
  const candidate={...docs[0],_id:new ObjectId(),product_id:Long('9000002'),sku:'TEST-P4',...change};
  let error;
  try { products.insertOne(candidate); } catch(e) {error=e;}
  verify(error && error.code===expectedCode,label+' rejected with code '+expectedCode);
  errors.push({label,expectedCode,actualCode:error.code,message:error.message});
}
rejected('Duplicate SKU',{sku:'KB-001'},11000);
rejected('Duplicate source product ID',{product_id:docs[0].product_id},11000);
rejected('Negative price',{price:Decimal128('-1')},121);
rejected('Binary double money',{price:1.5},121);
rejected('Wrong currency',{currency:'USD'},121);
rejected('Blank product name',{name:'   '},121);
rejected('Non-object attributes',{attributes:'USB'},121);
save('07-rejected-writes.ejson',errors);
const plan=products.find({sku:'KB-001'}).explain('executionStats');
save('08-sku-execution-plan.ejson',plan);
verify(JSON.stringify(plan.queryPlanner.winningPlan).includes('sku_unique'),
       'MongoDB naturally selects the unique SKU index for product lookup');
verify(plan.executionStats.nReturned===1 && plan.executionStats.totalDocsExamined===1,
       'Indexed SKU query returns and examines exactly one document');
verify(products.countDocuments({})===3,'Rejected writes leave the catalogue at three products');
save('09-indexes.ejson',products.getIndexes());
save('10-collection-options.ejson',lab.getCollectionInfos({name:'products'})[0].options);
save('11-final-catalogue.ejson',products.find().sort({sku:1}).toArray());
save('environment.ejson',{executed_at:new Date(),mongodb_version:lab.version(),
 database:databaseName,topology:'standalone, isolated Docker container',
 shell_version:version()});
fs.writeFileSync(out+'/verification.txt',checks.join('\n')+'\n');
print('Completed '+checks.length+' checks successfully.');
