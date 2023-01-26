# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Import Customer and Supplier Payment from Excel File',
    'version': '14.0.0.4',
    'sequence': 11,
    'category': 'Extra Tools',
    'summary': 'Apps helps for import customer payment import supplier payment import vendor payment import account payment import payment voucher import voucher import customer voucher import invoice import vendor bills import.',
    'description': """
	This module use for following easy import.
	odoo Import payment from CSV and Excel file Import customer payment from CSV and Excel file.
	odoo Import supplier payment import accouting payment Import customer and supplier payment from CSV and Excel file.
	odoo Import customer supplier payment Import payment details Import payment entry Import payment order odoo
	odoo Import payment invoice import vendor payment Import data Import files Import data from third party software
	odoo Import customer payment from CSV Import Bulk payment easily Import payment data Import payment order
    odoo Import accounting entry odoo customer payment import from CSV supplier payment import from CSV customer payment order import
    odoo  supplier payment order import Customer import Odoo CSV bridge Import CSV brige on Odoo
-Importar el pago desde el archivo CSV y Excel. -Importar el pago del cliente desde el archivo CSV y Excel.- Pago del proveedor de la importación, importación que acusa el pago-Importar el pago de clientes y proveedores desde el archivo CSV y Excel.-Importar pago de cliente / proveedor, detalles de pago de importación, entrada de pago de importación, orden de pago de importación.-Importar factura de pago, importar el pago del proveedor, Importar datos, Importar archivos, Importar datos de software de terceros- Importe el pago del cliente de CSV, importe el pago a granel fácilmente. Importe datos del pago, importe la orden del pago. Entrada de la contabilidad de la importación.- importación de pago de cliente de CSV, importación de pago de proveedor de CSV, importación de orden de pago de cliente, importación de orden de pago de proveedor - Importación de clientes, puente CSV Odoo, importación de brige CSV en Odoo


     -استلام دفعة العملاء من ملف CSV و Excel.
-استيراد المورد استيراد واستيراد الدفع accouting
-استيراد العملاء والموردين الدفع من ملف CSV و Excel.
-استيراد العملاء / المورد الدفع ، استيراد تفاصيل الدفع ، استيراد إدخال الدفع ، استيراد أمر الدفع.
فاتورة الدفع ، استيراد ، دفع بائع الاستيراد ، استيراد البيانات ، استيراد الملفات ، استيراد البيانات من برامج طرف ثالث
-استيراد العملاء الدفع من CSV ، استيراد الدفع السائبة بسهولة. استيراد بيانات الدفع ، استيراد أمر الدفع. إدخال المحاسبة المالية.
-استيراد الدفع من العملاء من CSV ، والمورد دفع الاستيراد من CSV ، وارادة ترتيب الدفع العملاء ، واستيراد المورد دفع النظام
     استيراد -Custom ، Odoo CSV الجسر ، استيراد CSV brige على Odoo

-Importation du paiement à partir du fichier CSV et Excel.
     -Importation du paiement du client à partir du fichier CSV et Excel.
-Payer le fournisseur d'importation, importer le paiement d'accouting
-Importation du paiement client et fournisseur à partir du fichier CSV et Excel.
-Importation du paiement client / fournisseur, des détails de paiement à l'importation, de l'entrée de paiement à l'importation, de l'ordre de paiement à l'importation.
-Facture de paiement d'importation, importation de paiement fournisseur, importation de données, importation de fichiers, importation de données à partir d'un logiciel tiers
-Importation du paiement client de CSV, importation en vrac paiement facilement.Importation des données de paiement, l'ordre de paiement d'importation.Import entrée comptable.
-l'importation de paiement à la clientèle de CSV, importation de paiement de fournisseur de CSV, importation d'ordre de paiement de client, importation d'ordre de paiement de fournisseur
     -Importation client, pont Odoo CSV, importation CSV brige sur Odoo

-Importar el pago desde el archivo CSV y Excel.
     -Importar el pago del cliente desde el archivo CSV y Excel.
- Pago del proveedor de la importación, importación que acusa el pago
-Importar el pago de clientes y proveedores desde el archivo CSV y Excel.
-Importar pago de cliente / proveedor, detalles de pago de importación, entrada de pago de importación, orden de pago de importación.
-Importar factura de pago, importar el pago del proveedor, Importar datos, Importar archivos, Importar datos de software de terceros
- Importe el pago del cliente de CSV, importe el pago a granel fácilmente. Importe datos del pago, importe la orden del pago. Entrada de la contabilidad de la importación.
- importación de pago de cliente de CSV, importación de pago de proveedor de CSV, importación de orden de pago de cliente, importación de orden de pago de proveedor
     - Importación de clientes, puente CSV Odoo, importación de brige CSV en Odoo

    """,
    'author': 'BrowseInfo',
    "price": 10,
    "currency": 'EUR',
    'website': 'https://www.browseinfo.in',
    'depends': ['base','account_payment'],
    'data': [
            'security/ir.model.access.csv',
             'views/customer_payment.xml',
	     
             ],
	
    'installable': True,
    'auto_install': False,
    "live_test_url":'https://youtu.be/i__YoBkJmTg',
	"images":['static/description/Banner.png'],
}

