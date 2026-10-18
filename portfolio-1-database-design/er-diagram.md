# MarketHub entity–relationship diagram

```mermaid
erDiagram
    CUSTOMERS ||--o{ CUSTOMER_ADDRESSES : saves
    CUSTOMERS ||--o{ ORDERS : places
    CATEGORIES ||--o{ PRODUCTS : classifies
    PRODUCTS ||--o| INVENTORY : has
    ORDERS ||--o{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : appears_in
    ORDERS ||--o{ PAYMENT_ATTEMPTS : receives
    ORDERS ||--o{ SHIPMENTS : dispatched_as

    CUSTOMERS {
        bigint customer_id PK
        varchar full_name
        varchar email UK
        varchar phone
        timestamptz created_at
    }
    CUSTOMER_ADDRESSES {
        bigint address_id PK
        bigint customer_id FK
        varchar recipient_name
        text address_line
        varchar city
        varchar state
        varchar postal_code
        varchar country
    }
    CATEGORIES {
        bigint category_id PK
        varchar category_name UK
    }
    PRODUCTS {
        bigint product_id PK
        bigint category_id FK
        varchar sku UK
        varchar product_name
        text description
        numeric current_price
        boolean is_active
    }
    INVENTORY {
        bigint product_id PK,FK
        integer quantity_on_hand
        integer reorder_level
    }
    ORDERS {
        bigint order_id PK
        bigint customer_id FK
        timestamptz ordered_at
        varchar status
        varchar delivery_recipient
        text delivery_address_line
        varchar delivery_city
        varchar delivery_state
        varchar delivery_postal_code
        varchar delivery_country
    }
    ORDER_ITEMS {
        bigint order_id PK,FK
        bigint product_id PK,FK
        integer quantity
        numeric unit_price
    }
    PAYMENT_ATTEMPTS {
        bigint payment_id PK
        bigint order_id FK
        varchar provider_reference UK
        numeric amount
        varchar status
        timestamptz attempted_at
    }
    SHIPMENTS {
        bigint shipment_id PK
        bigint order_id FK
        varchar carrier
        varchar tracking_number
        varchar status
        timestamptz shipped_at
        timestamptz delivered_at
    }
```

`||` means exactly one; `o{` means zero or many; `o|` means zero or one. A placed order must have one or more items, although drafts and the foreign-key structure allow zero. The product-creation workflow requires inventory even though the foreign key alone allows its absence. Tracking number is unique within its carrier, rather than globally unique.
