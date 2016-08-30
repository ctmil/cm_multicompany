# -*- coding: utf-8 -*-
from openerp import models, api, fields, exceptions
from openerp.exceptions import ValidationError
from datetime import date

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale_refund',
    'in_refund': 'purchase_refund',
}

class account_invoice(models.Model):
	_inherit = "account.invoice"


	@api.multi
	def onchange_company_id(self, company_id, part_id, type, invoice_line, currency_id):
        	# TODO: add the missing context parameter when forward-porting in trunk
	        # so we can remove this hack!
		self = self.with_context(self.env['res.users'].context_get())

		values = {}
		domain = {}

		if company_id and part_id and type:
			p = self.env['res.partner'].browse(part_id)
			if p.property_account_payable and p.property_account_receivable and \
	                    p.property_account_payable.company_id.id != company_id and \
        	            p.property_account_receivable.company_id.id != company_id:
                		prop = self.env['ir.property']
		                rec_dom = [('name', '=', 'property_account_receivable'), ('company_id', '=', company_id)]
		                pay_dom = [('name', '=', 'property_account_payable'), ('company_id', '=', company_id)]
		                res_dom = [('res_id', '=', 'res.partner,%s' % part_id)]
                		rec_prop = prop.search(rec_dom + res_dom) or prop.search(rec_dom)
		                pay_prop = prop.search(pay_dom + res_dom) or prop.search(pay_dom)
                		rec_account = rec_prop.get_by_record(rec_prop)
			        pay_account = pay_prop.get_by_record(pay_prop)
		                if not rec_account and not pay_account:
                		    action = self.env.ref('account.action_account_config')
		                    msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                		    raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

			if type in ('out_invoice', 'out_refund'):
				if company_id == 1:
			             #acc_id = rec_account.id
			        	acc_id = 11
				else:
					acc_id = 140
		        else:
	                	acc_id = pay_account.id
                	values= {'account_id': acc_id}

	        if self:
                	if company_id:
	                    for line in self.invoice_line:
        	                if not line.account_id:
                	            continue
                        	if line.account_id.company_id.id == company_id:
	                            continue
        	                accounts = self.env['account.account'].search([('name', '=', line.account_id.name), ('company_id', '=', company_id)])
                	        if not accounts:
                        	    action = self.env.ref('account.action_account_config')
	                            msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
        	                    raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
				if company_id == 1:
					taxes_id = [(6,0,[8])]
				else:
					taxes_id = [(6,0,[36])]
                	        line.write({'account_id': accounts[-1].id,'invoice_line_tax_id': taxes_id})
		        else:
		                for line_cmd in invoice_line or []:
                		    if len(line_cmd) >= 3 and isinstance(line_cmd[2], dict):
		                        line = self.env['account.account'].browse(line_cmd[2]['account_id'])
                		        if line.company_id.id != company_id:
		                            raise except_orm(
                		                _('Configuration Error!'),
                                		_("Invoice line account's company and invoice's company does not match.")
			                            )


		if company_id and type:
	            journal_type = TYPE2JOURNAL[type]
        	    journals = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', company_id)])
	            if journals:
        	        values['journal_id'] = journals[0].id
	            journal_defaults = self.env['ir.values'].get_defaults_dict('account.invoice', 'type=%s' % type)
        	    if 'journal_id' in journal_defaults:
                	values['journal_id'] = journal_defaults['journal_id']
	            if not values.get('journal_id'):
        	        field_desc = journals.fields_get(['type'])
                	type_label = next(t for t, label in field_desc['type']['selection'] if t == journal_type)
	                action = self.env.ref('account.action_account_journal_form')
        	        msg = _('Cannot find any account journal of type "%s" for this company, You should create one.\n Please go to Journal Configuration') % type_label
                	raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
	            domain = {'journal_id':  [('id', 'in', journals.ids)]}

        	return {'value': values, 'domain': domain}

