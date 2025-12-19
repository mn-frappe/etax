// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('eTax Invoice Link', {
    refresh: function(frm) {
        // Add action buttons based on status
        if (frm.doc.status === 'Pending' && !frm.is_new()) {
            frm.add_custom_button(__('View Reference'), function() {
                frappe.set_route('Form', frm.doc.reference_doctype, frm.doc.reference_name);
            });
        }
        
        // Set field descriptions in Mongolian
        frm.set_df_property('vat_type', 'description', 
            'Output = Борлуулалтын НӨАТ, Input = Худалдан авалтын НӨАТ');
    },
    
    reference_doctype: function(frm) {
        // Clear reference name when doctype changes
        frm.set_value('reference_name', null);
    },
    
    reference_name: function(frm) {
        // Auto-populate fields from reference document
        if (frm.doc.reference_doctype && frm.doc.reference_name) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: frm.doc.reference_doctype,
                    name: frm.doc.reference_name
                },
                callback: function(r) {
                    if (r.message) {
                        const doc = r.message;
                        frm.set_value('company', doc.company);
                        frm.set_value('posting_date', doc.posting_date);
                        
                        if (frm.doc.reference_doctype === 'Sales Invoice') {
                            frm.set_value('customer', doc.customer);
                            frm.set_value('vat_type', 'Output');
                        } else if (frm.doc.reference_doctype === 'Purchase Invoice') {
                            frm.set_value('supplier', doc.supplier);
                            frm.set_value('vat_type', 'Input');
                        }
                    }
                }
            });
        }
    }
});
