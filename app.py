import os
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from sqlalchemy import inspect, text

from models import db, Ingredient, MenuItem, RecipeItem, Order, OrderItem, StockMovement
from seed_data import seed_kebab_data

load_dotenv(override=True)

app = Flask(__name__)
CORS(app)

# Database Configuration (Support MySQL Local, SQLite local & Cloud PostgreSQL e.g. Supabase/Neon)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///dagangan.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg2://', 1)
elif database_url.startswith('postgresql://') and not database_url.startswith('postgresql+psycopg2://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
elif database_url.startswith('mysql://'):
    database_url = database_url.replace('mysql://', 'mysql+pymysql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    try:
        inspector = inspect(db.engine)
        if 'orders' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('orders')]
            if 'status' not in columns:
                db.session.execute(text("ALTER TABLE orders ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED'"))
                db.session.commit()
            if 'cancel_reason' not in columns:
                db.session.execute(text("ALTER TABLE orders ADD COLUMN cancel_reason VARCHAR(255) NULL"))
                db.session.commit()
            if 'cancelled_at' not in columns:
                db.session.execute(text("ALTER TABLE orders ADD COLUMN cancelled_at DATETIME NULL"))
                db.session.commit()
    except Exception as e:
        print(f"Warning during schema check: {e}")

    # Auto seed initial kebab data if empty
    seed_kebab_data()


@app.route('/')
def index():
    return jsonify({
        'status': 'online',
        'app_name': 'Kebab Commerce & Inventory API',
        'database': 'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite (Local)',
        'endpoints': {
            'menu': '/api/menu',
            'inventory': '/api/ingredients',
            'restock': '/api/inventory/restock',
            'orders_pos': '/api/orders',
            'daily_report': '/api/reports/daily',
            'summary_report': '/api/reports/summary'
        }
    })


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


# ==========================================================
# 1. INVENTORY & BAHAN BAKU (GET, POST, PUT, DELETE, RESTOCK)
# ==========================================================

@app.route('/api/ingredients', methods=['GET'])
def get_ingredients():
    ingredients = Ingredient.query.order_by(Ingredient.name.asc()).all()
    return jsonify({
        'status': 'success',
        'count': len(ingredients),
        'data': [ing.to_dict() for ing in ingredients]
    })


@app.route('/api/ingredients', methods=['POST'])
def add_ingredient():
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'status': 'error', 'message': 'Nama bahan wajib diisi'}), 400

    if Ingredient.query.filter_by(name=name).first():
        return jsonify({'status': 'error', 'message': f'Bahan "{name}" sudah ada'}), 400

    ing = Ingredient(
        name=name,
        unit=data.get('unit', 'pcs'),
        cost_per_unit=float(data.get('cost_per_unit', 0.0)),
        purchase_price=float(data.get('purchase_price', 0.0)),
        current_stock=float(data.get('current_stock', 0.0)),
        min_stock_alert=float(data.get('min_stock_alert', 5.0))
    )
    db.session.add(ing)
    db.session.commit()
    return jsonify({'status': 'success', 'data': ing.to_dict()}), 201


@app.route('/api/ingredients/<int:id>', methods=['PUT'])
def update_ingredient(id):
    ing = Ingredient.query.get_or_404(id)
    data = request.get_json() or {}

    if 'name' in data:
        ing.name = data['name']
    if 'unit' in data:
        ing.unit = data['unit']
    if 'cost_per_unit' in data:
        ing.cost_per_unit = float(data['cost_per_unit'])
    if 'purchase_price' in data:
        ing.purchase_price = float(data['purchase_price'])
    if 'current_stock' in data:
        ing.current_stock = float(data['current_stock'])
    if 'min_stock_alert' in data:
        ing.min_stock_alert = float(data['min_stock_alert'])

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Bahan berhasil diperbarui', 'data': ing.to_dict()})


@app.route('/api/ingredients/<int:id>', methods=['DELETE'])
def delete_ingredient(id):
    ing = Ingredient.query.get_or_404(id)
    db.session.delete(ing)
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'Bahan {ing.name} berhasil dihapus'})


@app.route('/api/inventory/restock', methods=['POST'])
def restock_inventory():
    data = request.get_json() or {}
    ing_id = data.get('ingredient_id')
    added_stock = float(data.get('added_stock', 0))

    if not ing_id or added_stock <= 0:
        return jsonify({'status': 'error', 'message': 'ingredient_id dan added_stock (>0) wajib diisi'}), 400

    ing = Ingredient.query.get_or_404(ing_id)
    prev_stock = ing.current_stock
    ing.current_stock += added_stock

    if 'purchase_cost' in data:
        ing.purchase_price = float(data['purchase_cost'])

    movement = StockMovement(
        ingredient_id=ing.id,
        type='RESTOCK',
        change_qty=added_stock,
        previous_stock=prev_stock,
        new_stock=ing.current_stock,
        reference=data.get('notes', 'Belanja Stok / Kulakan')
    )
    db.session.add(movement)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': f'Stok {ing.name} berhasil ditambah sebanyak {added_stock} {ing.unit}',
        'data': ing.to_dict()
    })


@app.route('/api/inventory/movements', methods=['GET'])
def get_stock_movements():
    movements = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(100).all()
    return jsonify({'status': 'success', 'data': [m.to_dict() for m in movements]})


# ==========================================================
# 2. MENU & RESEP (GET, PUT)
# ==========================================================

@app.route('/api/menu', methods=['GET'])
def get_menu():
    menus = MenuItem.query.filter_by(is_active=True).order_by(MenuItem.name.asc(), MenuItem.size.asc()).all()
    return jsonify({
        'status': 'success',
        'count': len(menus),
        'data': [m.to_dict(include_recipe=True) for m in menus]
    })


@app.route('/api/menu/<int:id>', methods=['PUT'])
def update_menu(id):
    menu = MenuItem.query.get_or_404(id)
    data = request.get_json() or {}

    if 'selling_price' in data:
        menu.selling_price = float(data['selling_price'])
    if 'hpp_real' in data:
        menu.hpp_real = float(data['hpp_real'])
    if 'name' in data:
        menu.name = data['name']
    if 'is_active' in data:
        menu.is_active = bool(data['is_active'])

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Menu berhasil diupdate', 'data': menu.to_dict()})


# ==========================================================
# 3. KASIR & TRANSAKSI PENJUALAN (POST ORDERS)
# ==========================================================

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json() or {}
    items_data = data.get('items', [])
    if not items_data:
        return jsonify({'status': 'error', 'message': 'Daftar menu pesanan (items) tidak boleh kosong'}), 400

    order_num = f"KB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    total_rev = 0.0
    total_hpp = 0.0

    order = Order(
        order_number=order_num,
        payment_method=data.get('payment_method', 'CASH'),
        notes=data.get('notes', '')
    )
    db.session.add(order)
    db.session.flush()

    for item in items_data:
        menu_id = item.get('menu_id')
        qty = int(item.get('quantity', 1))
        menu = MenuItem.query.get(menu_id)
        if not menu:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Menu ID {menu_id} tidak ditemukan'}), 404

        sub_rev = menu.selling_price * qty
        sub_hpp = menu.hpp_real * qty
        sub_prof = sub_rev - sub_hpp

        total_rev += sub_rev
        total_hpp += sub_hpp

        order_item = OrderItem(
            order_id=order.id,
            menu_id=menu.id,
            quantity=qty,
            unit_price=menu.selling_price,
            unit_hpp=menu.hpp_real,
            subtotal_revenue=sub_rev,
            subtotal_hpp=sub_hpp,
            subtotal_profit=sub_prof
        )
        db.session.add(order_item)

        # OTOMATIS POTONG STOK BAHAN BAKU BERDASARKAN RESEP!
        for recipe in menu.recipe_items:
            needed_qty = recipe.quantity_needed * qty
            ing = recipe.ingredient
            if ing:
                prev_stk = ing.current_stock
                ing.current_stock -= needed_qty

                movement = StockMovement(
                    ingredient_id=ing.id,
                    type='SALE',
                    change_qty=-needed_qty,
                    previous_stock=prev_stk,
                    new_stock=ing.current_stock,
                    reference=f'Pesanan #{order_num} ({menu.name} x{qty})'
                )
                db.session.add(movement)

    order.total_revenue = total_rev
    order.total_hpp = total_hpp
    order.gross_profit = total_rev - total_hpp

    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Pesanan berhasil diproses & stok bahan terpotong otomatis!',
        'data': order.to_dict()
    }), 201


@app.route('/api/orders', methods=['GET'])
def get_orders():
    date_str = request.args.get('date') # Format YYYY-MM-DD
    status_filter = request.args.get('status')
    query = Order.query

    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Order.created_at) == target_date)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Format tanggal harus YYYY-MM-DD'}), 400

    if status_filter:
        query = query.filter(Order.status == status_filter.upper())

    orders = query.order_by(Order.created_at.desc()).all()
    return jsonify({
        'status': 'success',
        'count': len(orders),
        'data': [o.to_dict() for o in orders]
    })


@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'status': 'error', 'message': f'Pesanan dengan ID {order_id} tidak ditemukan'}), 404

    if order.status == 'CANCELLED':
        return jsonify({'status': 'error', 'message': f'Pesanan #{order.order_number} sudah dibatalkan sebelumnya'}), 400

    data = request.get_json(silent=True) or {}
    reason = data.get('reason') or 'Dibatalkan oleh pelanggan'

    # 1. Update status order
    order.status = 'CANCELLED'
    order.cancel_reason = reason
    order.cancelled_at = datetime.utcnow()

    # 2. Kembalikan stok bahan baku (Rollback inventory stock)
    for item in order.items:
        menu = item.menu_item
        qty = item.quantity
        if menu:
            for recipe in menu.recipe_items:
                ing = recipe.ingredient
                if ing:
                    restored_qty = recipe.quantity_needed * qty
                    prev_stk = ing.current_stock
                    ing.current_stock += restored_qty

                    movement = StockMovement(
                        ingredient_id=ing.id,
                        type='CANCEL_RETURN',
                        change_qty=restored_qty,
                        previous_stock=prev_stk,
                        new_stock=ing.current_stock,
                        reference=f'Batal Pesanan #{order.order_number} ({menu.name} x{qty})'
                    )
                    db.session.add(movement)

    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': f'Pesanan #{order.order_number} berhasil dibatalkan dan seluruh stok bahan telah dikembalikan ke inventaris!',
        'data': order.to_dict()
    })


# ==========================================================
# 4. LAPORAN LABA HARIAN & KEUANGAN (DAILY REPORT)
# ==========================================================

@app.route('/api/reports/daily', methods=['GET'])
def daily_report():
    date_param = request.args.get('date')
    if date_param:
        try:
            query_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Format tanggal salah. Gunakan YYYY-MM-DD'}), 400
    else:
        query_date = date.today()

    all_orders = Order.query.filter(db.func.date(Order.created_at) == query_date).all()
    valid_orders = [o for o in all_orders if o.status != 'CANCELLED']
    cancelled_orders = [o for o in all_orders if o.status == 'CANCELLED']

    total_omzet = sum(o.total_revenue for o in valid_orders)
    total_hpp = sum(o.total_hpp for o in valid_orders)
    total_profit = sum(o.gross_profit for o in valid_orders)
    total_transactions = len(valid_orders)
    total_cancelled = len(cancelled_orders)

    # Hitung porsi terjual per menu (hanya pesanan valid)
    menu_sales = {}
    for o in valid_orders:
        for item in o.items:
            m_name = item.menu_name or f'Menu #{item.menu_id}'
            menu_sales[m_name] = menu_sales.get(m_name, 0) + item.quantity

    sorted_sales = sorted(menu_sales.items(), key=lambda x: x[1], reverse=True)

    # Cek peringatan stok menipis
    low_stocks = [ing.to_dict() for ing in Ingredient.query.all() if ing.current_stock <= ing.min_stock_alert]

    return jsonify({
        'status': 'success',
        'date': query_date.strftime('%Y-%m-%d'),
        'summary': {
            'total_transactions': total_transactions,
            'total_cancelled_transactions': total_cancelled,
            'total_omzet': total_omzet,
            'total_modal_hpp': total_hpp,
            'total_laba_bersih': total_profit,
            'profit_margin_percentage': round((total_profit / total_omzet * 100), 2) if total_omzet > 0 else 0.0
        },
        'menu_breakdown': [{'menu': name, 'portions_sold': qty} for name, qty in sorted_sales],
        'low_stock_alerts': low_stocks
    })


@app.route('/api/reports/summary', methods=['GET'])
def overall_summary():
    total_rev = db.session.query(db.func.sum(Order.total_revenue)).filter(Order.status != 'CANCELLED').scalar() or 0.0
    total_hpp = db.session.query(db.func.sum(Order.total_hpp)).filter(Order.status != 'CANCELLED').scalar() or 0.0
    total_profit = db.session.query(db.func.sum(Order.gross_profit)).filter(Order.status != 'CANCELLED').scalar() or 0.0
    total_tx = Order.query.filter(Order.status != 'CANCELLED').count()
    total_cancelled = Order.query.filter(Order.status == 'CANCELLED').count()

    return jsonify({
        'status': 'success',
        'overall': {
            'total_transactions': total_tx,
            'total_cancelled_transactions': total_cancelled,
            'total_omzet': total_rev,
            'total_modal_hpp': total_hpp,
            'total_laba': total_profit,
            'margin_percentage': round((total_profit / total_rev * 100), 2) if total_rev > 0 else 0.0
        }
    })


@app.route('/api/reports/trends', methods=['GET'])
def sales_trends():
    period = request.args.get('period', 'weekly').lower()  # 'weekly', 'monthly', 'yearly'
    today = date.today()
    orders_query = Order.query.filter(Order.status != 'CANCELLED')
    data_points = []

    if period == 'weekly':
        # 7 hari terakhir
        start_date = today - timedelta(days=6)
        orders = orders_query.filter(
            db.func.date(Order.created_at) >= start_date,
            db.func.date(Order.created_at) <= today
        ).all()

        agg = {}
        for o in orders:
            d_key = o.created_at.date().strftime('%Y-%m-%d')
            if d_key not in agg:
                agg[d_key] = {'omzet': 0.0, 'hpp': 0.0, 'laba': 0.0, 'count': 0}
            agg[d_key]['omzet'] += o.total_revenue
            agg[d_key]['hpp'] += o.total_hpp
            agg[d_key]['laba'] += o.gross_profit
            agg[d_key]['count'] += 1

        day_names_id = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
        for i in range(7):
            cur_date = start_date + timedelta(days=i)
            d_key = cur_date.strftime('%Y-%m-%d')
            day_name = day_names_id[cur_date.weekday()]
            short_label = f"{day_name}\n{cur_date.strftime('%d/%m')}"
            full_label = f"{day_name}, {cur_date.strftime('%d %b %Y')}"

            day_data = agg.get(d_key, {'omzet': 0.0, 'hpp': 0.0, 'laba': 0.0, 'count': 0})
            omzet = day_data['omzet']
            laba = day_data['laba']
            margin = round((laba / omzet * 100), 2) if omzet > 0 else 0.0

            data_points.append({
                'key': d_key,
                'short_label': short_label,
                'full_label': full_label,
                'date': d_key,
                'omzet': omzet,
                'modal_hpp': day_data['hpp'],
                'laba_bersih': laba,
                'margin_percentage': margin,
                'transactions': day_data['count']
            })

    elif period == 'monthly':
        # 30 hari terakhir
        start_date = today - timedelta(days=29)
        orders = orders_query.filter(
            db.func.date(Order.created_at) >= start_date,
            db.func.date(Order.created_at) <= today
        ).all()

        agg = {}
        for o in orders:
            d_key = o.created_at.date().strftime('%Y-%m-%d')
            if d_key not in agg:
                agg[d_key] = {'omzet': 0.0, 'hpp': 0.0, 'laba': 0.0, 'count': 0}
            agg[d_key]['omzet'] += o.total_revenue
            agg[d_key]['hpp'] += o.total_hpp
            agg[d_key]['laba'] += o.gross_profit
            agg[d_key]['count'] += 1

        day_names_id = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
        for i in range(30):
            cur_date = start_date + timedelta(days=i)
            d_key = cur_date.strftime('%Y-%m-%d')
            short_label = cur_date.strftime('%d/%m')
            day_name = day_names_id[cur_date.weekday()]
            full_label = f"{day_name}, {cur_date.strftime('%d %b %Y')}"

            day_data = agg.get(d_key, {'omzet': 0.0, 'hpp': 0.0, 'laba': 0.0, 'count': 0})
            omzet = day_data['omzet']
            laba = day_data['laba']
            margin = round((laba / omzet * 100), 2) if omzet > 0 else 0.0

            data_points.append({
                'key': d_key,
                'short_label': short_label,
                'full_label': full_label,
                'date': d_key,
                'omzet': omzet,
                'modal_hpp': day_data['hpp'],
                'laba_bersih': laba,
                'margin_percentage': margin,
                'transactions': day_data['count']
            })

    elif period == 'yearly':
        # 12 bulan terakhir
        orders = orders_query.all()
        agg = {}
        for o in orders:
            m_key = o.created_at.strftime('%Y-%m')
            if m_key not in agg:
                agg[m_key] = {'omzet': 0.0, 'hpp': 0.0, 'laba': 0.0, 'count': 0}
            agg[m_key]['omzet'] += o.total_revenue
            agg[m_key]['hpp'] += o.total_hpp
            agg[m_key]['laba'] += o.gross_profit
            agg[m_key]['count'] += 1

        month_names_id = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
        curr_y = today.year
        curr_m = today.month
        months_list = []
        for i in range(11, -1, -1):
            m = curr_m - i
            y = curr_y
            while m <= 0:
                m += 12
                y -= 1
            months_list.append((y, m))

        for y, m in months_list:
            m_key = f"{y:04d}-{m:02d}"
            short_label = f"{month_names_id[m]} '{str(y)[2:]}"
            full_label = f"{month_names_id[m]} {y}"

            m_data = agg.get(m_key, {'omzet': 0.0, 'hpp': 0.0, 'laba': 0.0, 'count': 0})
            omzet = m_data['omzet']
            laba = m_data['laba']
            margin = round((laba / omzet * 100), 2) if omzet > 0 else 0.0

            data_points.append({
                'key': m_key,
                'short_label': short_label,
                'full_label': full_label,
                'date': m_key,
                'omzet': omzet,
                'modal_hpp': m_data['hpp'],
                'laba_bersih': laba,
                'margin_percentage': margin,
                'transactions': m_data['count']
            })

    total_omzet = sum(p['omzet'] for p in data_points)
    total_hpp = sum(p['modal_hpp'] for p in data_points)
    total_laba = sum(p['laba_bersih'] for p in data_points)
    total_tx = sum(p['transactions'] for p in data_points)
    n_points = len(data_points)
    avg_omzet = round(total_omzet / n_points, 2) if n_points > 0 else 0.0
    avg_laba = round(total_laba / n_points, 2) if n_points > 0 else 0.0
    overall_margin = round((total_laba / total_omzet * 100), 2) if total_omzet > 0 else 0.0

    peak_point = max(data_points, key=lambda x: x['omzet']) if data_points else None

    return jsonify({
        'status': 'success',
        'period': period,
        'summary': {
            'total_omzet': total_omzet,
            'total_modal_hpp': total_hpp,
            'total_laba_bersih': total_laba,
            'total_transactions': total_tx,
            'average_omzet': avg_omzet,
            'average_laba_bersih': avg_laba,
            'margin_percentage': overall_margin,
            'peak_point': peak_point
        },
        'points': data_points
    })



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'Starting Kebab Dagang Backend Server on port {port}...')
    app.run(host='0.0.0.0', port=port, debug=True)
