# API Reference

## Whitelisted Methods

### Tax Operations

#### `etax.api.submit_declaration`

Submit tax declaration to MTA.

```python
import frappe

result = frappe.call(
    "etax.api.submit_declaration",
    declaration_type="VAT",
    period="2024-12"
)
```

---

#### `etax.api.get_declaration_status`

Check declaration status.

```python
result = frappe.call(
    "etax.api.get_declaration_status",
    declaration_id="dec_123"
)
```

---

#### `etax.api.validate_tin`

Validate taxpayer identification number.

```python
result = frappe.call(
    "etax.api.validate_tin",
    tin="1234567"
)
```

## JavaScript API

```javascript
frappe.call({
    method: "etax.api.submit_declaration",
    args: {
        declaration_type: "VAT",
        period: "2024-12"
    },
    callback: function(r) {
        console.log(r.message);
    }
});
```
