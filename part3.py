from flask import Flask, jsonify, request
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, joinedload
from models import db, Company, Warehouse, Product, Inventory, Supplier, SupplierProduct, Sales  # assumed model classes
from datetime import datetime, timedelta

app = Flask(_name_)

@app.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
def low_stock_alerts(company_id):
    try:
        recent_days = 30
        session = db.session

        # Get all warehouses for this company
        warehouses = session.query(Warehouse).filter_by(company_id=company_id).all()
        warehouse_ids = [w.id for w in warehouses]

        alerts = []
        for wid in warehouse_ids:
            # Find all inventory items in the warehouse
            inventory_items = session.query(Inventory).filter_by(warehouse_id=wid).all()

            for item in inventory_items:
                product = session.query(Product).filter_by(id=item.product_id).first()

                # Skip if threshold is not set or product is a bundle
                if not product or product.is_bundle or product.threshold is None:
                    continue

                # Check recent sales for product in warehouse
                recent_sales = session.query(Sales).filter(
                    Sales.product_id == product.id,
                    Sales.warehouse_id == wid,
                    Sales.sale_date >= datetime.utcnow() - timedelta(days=recent_days)
                ).all()

                if not recent_sales:
                    continue  # skip products with no recent sales

                # Calculate sales rate (average per day)
                total_sold = sum([s.quantity for s in recent_sales])
                avg_daily_sales = total_sold / recent_days if total_sold > 0 else 0.1  # prevent div by zero
                days_until_stockout = item.quantity / avg_daily_sales if avg_daily_sales > 0 else -1

                # Low stock condition
                if item.quantity < product.threshold:
                    # Find supplier (just get one for now)
                    supplier = session.query(Supplier).join(SupplierProduct).filter(
                        SupplierProduct.product_id == product.id
                    ).first()

                    alerts.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "sku": product.sku,
                        "warehouse_id": wid,
                        "warehouse_name": session.query(Warehouse).get(wid).name,
                        "current_stock": item.quantity,
                        "threshold": product.threshold,
                        "days_until_stockout": round(days_until_stockout, 2),
                        "supplier": {
                            "id": supplier.id if supplier else None,
                            "name": supplier.name if supplier else None,
                            "contact_email": supplier.email if supplier else None
                        }
                    })

        return jsonify({"alerts": alerts, "total_alerts": len(alerts)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ensure app is run only when called directly
if _name_ == '_main_':
    app.run(debug=True)