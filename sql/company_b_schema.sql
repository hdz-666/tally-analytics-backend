-- ─────────────────────────────────────────────────────────────────────────────
-- Company B schema — same table structure as "tally db" (Company A)
-- Run this once in Supabase SQL editor.
-- Then point tally-database-loader at schema "company_b" when syncing Company B.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS company_b;

CREATE TABLE IF NOT EXISTS company_b.config (
    name varchar(64) PRIMARY KEY,
    value varchar(1024)
);

CREATE TABLE IF NOT EXISTS company_b.mst_group (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    primary_group varchar(1024),
    is_revenue boolean,
    is_deemedpositive boolean,
    is_reserved boolean,
    affects_gross_profit boolean,
    sort_position integer
);

CREATE TABLE IF NOT EXISTS company_b.mst_ledger (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    alias varchar(256),
    description varchar(64),
    notes varchar(64),
    is_revenue boolean,
    is_deemedpositive boolean,
    opening_balance numeric(17,2),
    closing_balance numeric(17,2),
    mailing_name varchar(256),
    mailing_address varchar(1024),
    mailing_state varchar(256),
    mailing_country varchar(256),
    mailing_pincode varchar(64),
    email varchar(256),
    mobile varchar(32),
    it_pan varchar(64),
    gstn varchar(64),
    gst_registration_type varchar(64),
    gst_supply_type varchar(64),
    gst_duty_head varchar(16),
    bank_account_holder varchar(256),
    bank_account_number varchar(64),
    bank_ifsc varchar(64),
    bank_swift varchar(64),
    bank_name varchar(64),
    bank_branch varchar(64),
    bill_credit_period integer
);

CREATE TABLE IF NOT EXISTS company_b.mst_vouchertype (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    numbering_method varchar(64),
    is_deemedpositive boolean,
    affects_stock boolean
);

CREATE TABLE IF NOT EXISTS company_b.mst_uom (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    formalname varchar(256),
    is_simple_unit boolean,
    base_units varchar(1024),
    additional_units varchar(1024),
    conversion numeric(15,4)
);

CREATE TABLE IF NOT EXISTS company_b.mst_godown (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    address varchar(1024)
);

CREATE TABLE IF NOT EXISTS company_b.mst_stock_category (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024)
);

CREATE TABLE IF NOT EXISTS company_b.mst_stock_group (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024)
);

CREATE TABLE IF NOT EXISTS company_b.mst_stock_item (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    category varchar(1024),
    alias varchar(256),
    description varchar(64),
    notes varchar(64),
    part_number varchar(256),
    uom varchar(32),
    alternate_uom varchar(32),
    conversion numeric(15,4),
    opening_balance numeric(15,4),
    opening_rate numeric(15,4),
    opening_value numeric(17,2),
    closing_balance numeric(15,4),
    closing_rate numeric(15,4),
    closing_value numeric(17,2),
    costing_method varchar(32),
    gst_type_of_supply varchar(32),
    gst_hsn_code varchar(64),
    gst_hsn_description varchar(256),
    gst_rate numeric(9,4),
    gst_taxability varchar(32)
);

CREATE TABLE IF NOT EXISTS company_b.mst_cost_category (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    allocate_revenue boolean,
    allocate_non_revenue boolean
);

CREATE TABLE IF NOT EXISTS company_b.mst_cost_centre (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    category varchar(1024)
);

CREATE TABLE IF NOT EXISTS company_b.mst_attendance_type (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    uom varchar(32),
    attendance_type varchar(64),
    attendance_period varchar(64)
);

CREATE TABLE IF NOT EXISTS company_b.mst_employee (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    id_number varchar(256),
    date_of_joining date,
    date_of_release date,
    designation varchar(64),
    function_role varchar(64),
    location varchar(256),
    gender varchar(32),
    date_of_birth date,
    blood_group varchar(32),
    father_mother_name varchar(256),
    spouse_name varchar(256),
    address varchar(256),
    mobile varchar(32),
    email varchar(64),
    pan varchar(32),
    aadhar varchar(32),
    uan varchar(32),
    pf_number varchar(32),
    pf_joining_date date,
    pf_relieving_date date,
    pr_account_number varchar(32)
);

CREATE TABLE IF NOT EXISTS company_b.mst_payhead (
    guid varchar(64) PRIMARY KEY,
    name varchar(1024),
    parent varchar(1024),
    payslip_name varchar(1024),
    pay_type varchar(64),
    income_type varchar(64),
    calculation_type varchar(32),
    leave_type varchar(64),
    calculation_period varchar(32)
);

CREATE TABLE IF NOT EXISTS company_b.mst_gst_effective_rate (
    item varchar(1024),
    applicable_from date,
    hsn_description varchar(256),
    hsn_code varchar(64),
    duty_head varchar(64),
    rate numeric(9,4),
    rate_per_unit numeric(9,4),
    valuation_type varchar(64),
    is_rcm_applicable boolean,
    nature_of_transaction varchar(64),
    nature_of_goods varchar(64),
    supply_type varchar(64),
    taxability varchar(64)
);

CREATE TABLE IF NOT EXISTS company_b.mst_opening_batch_allocation (
    name varchar(1024),
    item varchar(1024),
    opening_balance numeric(15,4),
    opening_rate numeric(15,4),
    opening_value numeric(17,2),
    godown varchar(1024),
    manufactured_on date
);

CREATE TABLE IF NOT EXISTS company_b.mst_opening_bill_allocation (
    ledger varchar(1024),
    opening_balance numeric(17,4),
    bill_date date,
    name varchar(1024),
    bill_credit_period integer,
    is_advance boolean
);

CREATE TABLE IF NOT EXISTS company_b.trn_closingstock_ledger (
    ledger varchar(1024),
    stock_date date,
    stock_value numeric(17,2)
);

CREATE TABLE IF NOT EXISTS company_b.mst_stockitem_standard_cost (
    item varchar(1024),
    date date,
    rate numeric(15,4)
);

CREATE TABLE IF NOT EXISTS company_b.mst_stockitem_standard_price (
    item varchar(1024),
    date date,
    rate numeric(15,4)
);

CREATE TABLE IF NOT EXISTS company_b.trn_voucher (
    guid varchar(64) PRIMARY KEY,
    date date,
    voucher_type varchar(1024),
    voucher_number varchar(64),
    reference_number varchar(64),
    reference_date date,
    narration varchar(4000),
    party_name varchar(256),
    place_of_supply varchar(256),
    is_invoice boolean,
    is_accounting_voucher boolean,
    is_inventory_voucher boolean,
    is_order_voucher boolean
);

CREATE TABLE IF NOT EXISTS company_b.trn_accounting (
    guid varchar(64),
    ledger varchar(1024),
    amount numeric(17,2),
    amount_forex numeric(17,2),
    currency varchar(16)
);

CREATE TABLE IF NOT EXISTS company_b.trn_inventory (
    guid varchar(64),
    item varchar(1024),
    quantity numeric(15,4),
    rate numeric(15,4),
    amount numeric(17,2),
    additional_amount numeric(17,2),
    discount_amount numeric(17,2),
    godown varchar(1024),
    tracking_number varchar(256),
    order_number varchar(256),
    order_duedate date
);

CREATE TABLE IF NOT EXISTS company_b.trn_cost_centre (
    guid varchar(64),
    ledger varchar(1024),
    costcentre varchar(1024),
    amount numeric(17,2)
);

CREATE TABLE IF NOT EXISTS company_b.trn_cost_category_centre (
    guid varchar(64),
    ledger varchar(1024),
    costcategory varchar(1024),
    costcentre varchar(1024),
    amount numeric(17,2)
);

CREATE TABLE IF NOT EXISTS company_b.trn_cost_inventory_category_centre (
    guid varchar(64),
    ledger varchar(1024),
    item varchar(1024),
    costcategory varchar(1024),
    costcentre varchar(1024),
    amount numeric(17,2)
);

CREATE TABLE IF NOT EXISTS company_b.trn_bill (
    guid varchar(64),
    ledger varchar(1024),
    name varchar(1024),
    amount numeric(17,2),
    billtype varchar(256),
    bill_credit_period integer
);

CREATE TABLE IF NOT EXISTS company_b.trn_bank (
    guid varchar(64),
    ledger varchar(1024),
    transaction_type varchar(32),
    instrument_date date,
    instrument_number varchar(1024),
    bank_name varchar(64),
    amount numeric(17,2),
    bankers_date date
);

CREATE TABLE IF NOT EXISTS company_b.trn_batch (
    guid varchar(64),
    item varchar(1024),
    name varchar(1024),
    quantity numeric(15,4),
    amount numeric(17,2),
    godown varchar(1024),
    destination_godown varchar(1024),
    tracking_number varchar(1024)
);

CREATE TABLE IF NOT EXISTS company_b.trn_inventory_additional_cost (
    guid varchar(64),
    ledger varchar(1024),
    amount numeric(17,2),
    additional_allocation_type varchar(32),
    rate_of_invoice_tax numeric(9,4)
);

CREATE TABLE IF NOT EXISTS company_b.trn_employee (
    guid varchar(64),
    category varchar(1024),
    employee_name varchar(1024),
    amount numeric(17,2),
    employee_sort_order integer
);

CREATE TABLE IF NOT EXISTS company_b.trn_payhead (
    guid varchar(64),
    category varchar(1024),
    employee_name varchar(1024),
    employee_sort_order integer,
    payhead_name varchar(1024),
    payhead_sort_order integer,
    amount numeric(17,2)
);

CREATE TABLE IF NOT EXISTS company_b.trn_attendance (
    guid varchar(64),
    employee_name varchar(1024),
    attendancetype_name varchar(1024),
    time_value numeric(17,2),
    type_value numeric(17,2)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_b_trn_voucher_date
    ON company_b.trn_voucher(date);
CREATE INDEX IF NOT EXISTS idx_b_trn_accounting_guid
    ON company_b.trn_accounting(guid);
CREATE INDEX IF NOT EXISTS idx_b_trn_inventory_guid
    ON company_b.trn_inventory(guid);
CREATE INDEX IF NOT EXISTS idx_b_mst_stock_item_name
    ON company_b.mst_stock_item(name);
