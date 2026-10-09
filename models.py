from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Ingredient(db.Model):
    __tablename__ = 'ingredients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    unit = db.Column(db.String(20), nullable=False, default='pcs') # pcs, slice, gram, porsi
    cost_per_unit = db.Column(db.Float, nullable=False, default=0.0) # Biaya per resep
    purchase_price = db.Column(db.Float, nullable=False, default=0.0) # Harga beli kulakan
    current_stock = db.Column(db.Float, nullable=False, default=0.0) # Sisa stok saat ini
    min_stock_alert = db.Column(db.Float, nullable=False, default=5.0) # Ambang batas peringatan stok menipis
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'unit': self.unit,
            'cost_per_unit': self.cost_per_unit,
            'purchase_price': self.purchase_price,
            'current_stock': self.current_stock,
            'min_stock_alert': self.min_stock_alert,
            'is_low_stock': self.current_stock <= self.min_stock_alert
        }


class MenuItem(db.Model):
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True) # e.g. ORI-CHK-REG
    name = db.Column(db.String(100), nullable=False) # e.g. Original Chicken
    size = db.Column(db.String(20), nullable=False) # Regular / Large
    hpp_real = db.Column(db.Float, nullable=False, default=0.0) # HPP
    selling_price = db.Column(db.Float, nullable=False, default=0.0) # Harga Jual
    is_active = db.Column(db.Boolean, default=True)

    recipe_items = db.relationship('RecipeItem', backref='menu_item', lazy=True, cascade='all, delete-orphan')

    @property
    def estimated_profit(self):
        return self.selling_price - self.hpp_real

    def to_dict(self, include_recipe=False):
        data = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'size': self.size,
            'hpp_real': self.hpp_real,
            'selling_price': self.selling_price,
            'estimated_profit': self.estimated_profit,
            'is_active': self.is_active
        }
        if include_recipe:
            data['recipes'] = [r.to_dict() for r in self.recipe_items]
        return data


class RecipeItem(db.Model):
    __tablename__ = 'recipe_items'

    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity_needed = db.Column(db.Float, nullable=False, default=1.0) # Berapa qty bahan yang dipakai per 1 porsi menu

    ingredient = db.relationship('Ingredient', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'unit': self.ingredient.unit if self.ingredient else None,
            'quantity_needed': self.quantity_needed,
            'cost': (self.ingredient.cost_per_unit * self.quantity_needed) if self.ingredient else 0.0
        }


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_revenue = db.Column(db.Float, nullable=False, default=0.0) # Total Omzet
    total_hpp = db.Column(db.Float, nullable=False, default=0.0) # Total Modal Bahan
    gross_profit = db.Column(db.Float, nullable=False, default=0.0) # Laba Kotor
    payment_method = db.Column(db.String(20), default='CASH') # CASH, QRIS, TRANSFER
    notes = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='COMPLETED') # COMPLETED, CANCELLED
    cancel_reason = db.Column(db.String(255), nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'total_revenue': self.total_revenue,
            'total_hpp': self.total_hpp,
            'gross_profit': self.gross_profit,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'status': self.status,
            'cancel_reason': self.cancel_reason,
            'cancelled_at': self.cancelled_at.strftime('%Y-%m-%d %H:%M:%S') if self.cancelled_at else None,
            'items': [item.to_dict() for item in self.items]
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    unit_hpp = db.Column(db.Float, nullable=False, default=0.0)
    subtotal_revenue = db.Column(db.Float, nullable=False, default=0.0)
    subtotal_hpp = db.Column(db.Float, nullable=False, default=0.0)
    subtotal_profit = db.Column(db.Float, nullable=False, default=0.0)

    menu_item = db.relationship('MenuItem', lazy=True)

    @property
    def menu_name(self):
        return f'{self.menu_item.name} ({self.menu_item.size})' if self.menu_item else None

    def to_dict(self):
        return {
            'id': self.id,
            'menu_id': self.menu_id,
            'menu_name': self.menu_name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'unit_hpp': self.unit_hpp,
            'subtotal_revenue': self.subtotal_revenue,
            'subtotal_hpp': self.subtotal_hpp,
            'subtotal_profit': self.subtotal_profit
        }


class StockMovement(db.Model):
    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False) # SALE (terjual), RESTOCK (belanja), ADJUSTMENT (koreksi)
    change_qty = db.Column(db.Float, nullable=False) # Bisa minus (terjual) atau plus (kulakan)
    previous_stock = db.Column(db.Float, nullable=False)
    new_stock = db.Column(db.Float, nullable=False)
    reference = db.Column(db.String(100), nullable=True) # e.g. Order #KB-20261006-001
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ingredient = db.relationship('Ingredient', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'type': self.type,
            'change_qty': self.change_qty,
            'previous_stock': self.previous_stock,
            'new_stock': self.new_stock,
            'reference': self.reference,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
