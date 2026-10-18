-- PostgreSQL; run once in a fresh practice database.
BEGIN;
CREATE SCHEMA markethub;
SET LOCAL search_path TO markethub, public;

CREATE TABLE customers (
    customer_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name varchar(150) NOT NULL CHECK (btrim(full_name) <> ''),
    email varchar(254) NOT NULL UNIQUE
        CHECK (email = lower(btrim(email)) AND email <> ''),
    phone varchar(30),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customer_addresses (
    address_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES customers ON DELETE RESTRICT,
    recipient_name varchar(150) NOT NULL CHECK (btrim(recipient_name) <> ''),
    address_line text NOT NULL CHECK (btrim(address_line) <> ''),
    city varchar(100) NOT NULL CHECK (btrim(city) <> ''),
    state varchar(100) NOT NULL CHECK (btrim(state) <> ''),
    postal_code varchar(20),
    country varchar(100) NOT NULL DEFAULT 'Nigeria' CHECK (btrim(country) <> '')
);

CREATE TABLE categories (
    category_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_name varchar(100) NOT NULL UNIQUE CHECK (btrim(category_name) <> '')
);

CREATE TABLE products (
    product_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id bigint NOT NULL REFERENCES categories ON DELETE RESTRICT,
    sku varchar(50) NOT NULL UNIQUE CHECK (btrim(sku) <> ''),
    product_name varchar(200) NOT NULL CHECK (btrim(product_name) <> ''),
    description text,
    current_price numeric(12,2) NOT NULL CHECK (current_price >= 0),
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE inventory (
    product_id bigint PRIMARY KEY REFERENCES products ON DELETE RESTRICT,
    quantity_on_hand integer NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    reorder_level integer NOT NULL DEFAULT 5 CHECK (reorder_level >= 0)
);

CREATE TABLE orders (
    order_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES customers ON DELETE RESTRICT,
    ordered_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status varchar(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','placed','paid','shipped','delivered','cancelled')),
    delivery_recipient varchar(150) NOT NULL CHECK (btrim(delivery_recipient) <> ''),
    delivery_address_line text NOT NULL CHECK (btrim(delivery_address_line) <> ''),
    delivery_city varchar(100) NOT NULL CHECK (btrim(delivery_city) <> ''),
    delivery_state varchar(100) NOT NULL CHECK (btrim(delivery_state) <> ''),
    delivery_postal_code varchar(20),
    delivery_country varchar(100) NOT NULL DEFAULT 'Nigeria'
        CHECK (btrim(delivery_country) <> '')
);

CREATE TABLE order_items (
    order_id bigint NOT NULL REFERENCES orders ON DELETE RESTRICT,
    product_id bigint NOT NULL REFERENCES products ON DELETE RESTRICT,
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price numeric(12,2) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE payment_attempts (
    payment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id bigint NOT NULL REFERENCES orders ON DELETE RESTRICT,
    provider_reference varchar(150) NOT NULL UNIQUE
        CHECK (btrim(provider_reference) <> ''),
    amount numeric(12,2) NOT NULL CHECK (amount > 0),
    status varchar(20) NOT NULL
        CHECK (status IN ('pending','successful','failed')),
    attempted_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX one_successful_payment_per_order
    ON payment_attempts(order_id) WHERE status = 'successful';

CREATE TABLE shipments (
    shipment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id bigint NOT NULL REFERENCES orders ON DELETE RESTRICT,
    carrier varchar(100) NOT NULL CHECK (btrim(carrier) <> ''),
    tracking_number varchar(100) NOT NULL CHECK (btrim(tracking_number) <> ''),
    status varchar(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','in_transit','delivered')),
    shipped_at timestamptz,
    delivered_at timestamptz,
    UNIQUE (carrier, tracking_number),
    CHECK (delivered_at IS NULL OR
        (shipped_at IS NOT NULL AND delivered_at >= shipped_at)),
    CHECK ((status = 'pending' AND shipped_at IS NULL AND delivered_at IS NULL)
        OR (status = 'in_transit' AND shipped_at IS NOT NULL AND delivered_at IS NULL)
        OR (status = 'delivered' AND shipped_at IS NOT NULL AND delivered_at IS NOT NULL))
);

-- FK indexes support joins and checks on referenced rows.
CREATE INDEX addresses_customer_idx ON customer_addresses(customer_id);
CREATE INDEX products_category_idx ON products(category_id);
CREATE INDEX orders_customer_idx ON orders(customer_id);
CREATE INDEX order_items_product_idx ON order_items(product_id);
CREATE INDEX payment_attempts_order_idx ON payment_attempts(order_id);
CREATE INDEX shipments_order_idx ON shipments(order_id);
COMMIT;
