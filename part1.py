from flask import request, jsonify
from sqlalchemy.exc import IntegrityError
from models import Product, Inventory, db  # assuming these exist
from decimal import Decimal, InvalidOperation

@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity']
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    
    # Type and business rule checks
    try:
        price = Decimal(data['price'])
        if price <= 0:
            return jsonify({"error": "Price must be greater than zero"}), 400
    except (InvalidOperation, TypeError):
        return jsonify({"error": "Invalid price format"}), 400

    try:
        quantity = int(data['initial_quantity'])
        if quantity < 0:
            return jsonify({"error": "Quantity cannot be negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid quantity"}), 400

    # Check SKU uniqueness
    existing_product = Product.query.filter_by(sku=data['sku']).first()
    if existing_product:
        return jsonify({"error": "SKU already exists"}), 409

    # Begin atomic transaction
    try:
        product = Product(
            name=data['name'],
            sku=data['sku'],
            price=price
        )
        db.session.add(product)
        db.session.flush()  # get product.id before commit

        inventory = Inventory(
            product_id=product.id,
            warehouse_id=data['warehouse_id'],
            quantity=quantity
        )
        db.session.add(inventory)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity error", "details": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500

    return jsonify({"message": "Product created", "product_id": product.id}), 201