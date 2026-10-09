from models import db, Ingredient, MenuItem, RecipeItem

def seed_kebab_data():
    if Ingredient.query.first():
        print('Database already contains data. Skipping initial seeding.')
        return

    print('Seeding ingredients from Preparation_Kebab document...')
    ingredients_data = [
        {'name': 'Tortilla Large', 'unit': 'pcs', 'cost_per_unit': 3000, 'purchase_price': 38000, 'stock': 50},
        {'name': 'Tortilla Regular', 'unit': 'pcs', 'cost_per_unit': 1500, 'purchase_price': 27000, 'stock': 50},
        {'name': 'Selada / Lettuce', 'unit': 'pcs', 'cost_per_unit': 1000, 'purchase_price': 15000, 'stock': 60},
        {'name': 'Keju Slice Melt', 'unit': 'pcs', 'cost_per_unit': 3000, 'purchase_price': 45000, 'stock': 40},
        {'name': 'Mentega', 'unit': 'portion', 'cost_per_unit': 2000, 'purchase_price': 26000, 'stock': 80},
        {'name': 'Ayam Filet Dada', 'unit': 'slice', 'cost_per_unit': 3000, 'purchase_price': 45000, 'stock': 50},
        {'name': 'Beef Smoke / Slice', 'unit': 'slice', 'cost_per_unit': 2000, 'purchase_price': 28000, 'stock': 60},
        {'name': 'Telur', 'unit': 'pcs', 'cost_per_unit': 3000, 'purchase_price': 30000, 'stock': 40},
        {'name': 'Sosis Sapi', 'unit': 'pcs', 'cost_per_unit': 3000, 'purchase_price': 57000, 'stock': 35},
        {'name': 'Bumbu Kering', 'unit': 'portion', 'cost_per_unit': 4500, 'purchase_price': 87000, 'stock': 100},
        {'name': 'Saus & Mayo', 'unit': 'portion', 'cost_per_unit': 4000, 'purchase_price': 77000, 'stock': 100},
    ]

    ing_map = {}
    for item in ingredients_data:
        ing = Ingredient(
            name=item['name'],
            unit=item['unit'],
            cost_per_unit=item['cost_per_unit'],
            purchase_price=item['purchase_price'],
            current_stock=item['stock'],
            min_stock_alert=10
        )
        db.session.add(ing)
        db.session.flush()
        ing_map[item['name']] = ing.id

    print('Seeding menus and recipes...')
    menus_data = [
        {
            'code': 'ORI-CHK-REG', 'name': 'Original Chicken', 'size': 'Regular',
            'hpp': 10000, 'price': 15000,
            'recipe': [('Tortilla Regular', 1), ('Selada / Lettuce', 1), ('Ayam Filet Dada', 0.5), ('Saus & Mayo', 1)]
        },
        {
            'code': 'ORI-CHK-LRG', 'name': 'Original Chicken', 'size': 'Large',
            'hpp': 13000, 'price': 18000,
            'recipe': [('Tortilla Large', 1), ('Selada / Lettuce', 1), ('Ayam Filet Dada', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'ORI-BEF-REG', 'name': 'Original Beef', 'size': 'Regular',
            'hpp': 10500, 'price': 15000,
            'recipe': [('Tortilla Regular', 1), ('Selada / Lettuce', 1), ('Beef Smoke / Slice', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'ORI-BEF-LRG', 'name': 'Original Beef', 'size': 'Large',
            'hpp': 14000, 'price': 19000,
            'recipe': [('Tortilla Large', 1), ('Selada / Lettuce', 1), ('Beef Smoke / Slice', 2), ('Saus & Mayo', 1)]
        },
        {
            'code': 'CHK-EGG-REG', 'name': 'Chicken Easter Egg', 'size': 'Regular',
            'hpp': 13000, 'price': 18000,
            'recipe': [('Tortilla Regular', 1), ('Selada / Lettuce', 1), ('Ayam Filet Dada', 0.5), ('Telur', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'CHK-EGG-LRG', 'name': 'Chicken Easter Egg', 'size': 'Large',
            'hpp': 16000, 'price': 22000,
            'recipe': [('Tortilla Large', 1), ('Selada / Lettuce', 1), ('Ayam Filet Dada', 1), ('Telur', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'BEF-EGG-REG', 'name': 'Beef Easter Egg', 'size': 'Regular',
            'hpp': 13500, 'price': 19000,
            'recipe': [('Tortilla Regular', 1), ('Selada / Lettuce', 1), ('Beef Smoke / Slice', 1), ('Telur', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'BEF-EGG-LRG', 'name': 'Beef Easter Egg', 'size': 'Large',
            'hpp': 17000, 'price': 23000,
            'recipe': [('Tortilla Large', 1), ('Selada / Lettuce', 1), ('Beef Smoke / Slice', 2), ('Telur', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'CHK-CHS-REG', 'name': 'Chicken Cheesy Egged', 'size': 'Regular',
            'hpp': 16000, 'price': 22000,
            'recipe': [('Tortilla Regular', 1), ('Selada / Lettuce', 1), ('Ayam Filet Dada', 0.5), ('Telur', 1), ('Keju Slice Melt', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'CHK-CHS-LRG', 'name': 'Chicken Cheesy Egged', 'size': 'Large',
            'hpp': 19000, 'price': 25000,
            'recipe': [('Tortilla Large', 1), ('Selada / Lettuce', 1), ('Ayam Filet Dada', 1), ('Telur', 1), ('Keju Slice Melt', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'BEF-CHS-REG', 'name': 'Beef Cheesy Egged', 'size': 'Regular',
            'hpp': 16500, 'price': 23000,
            'recipe': [('Tortilla Regular', 1), ('Selada / Lettuce', 1), ('Beef Smoke / Slice', 1), ('Telur', 1), ('Keju Slice Melt', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'BEF-CHS-LRG', 'name': 'Beef Cheesy Egged', 'size': 'Large',
            'hpp': 20000, 'price': 26000,
            'recipe': [('Tortilla Large', 1), ('Selada / Lettuce', 1), ('Beef Smoke / Slice', 2), ('Telur', 1), ('Keju Slice Melt', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'SPC-CHK-REG', 'name': 'Special Chicken', 'size': 'Regular',
            'hpp': 17500, 'price': 24000,
            'recipe': [('Tortilla Regular', 1), ('Selada / Lettuce', 1), ('Ayam Filet Dada', 0.5), ('Sosis Sapi', 0.5), ('Telur', 1), ('Keju Slice Melt', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'SPC-CHK-LRG', 'name': 'Special Chicken', 'size': 'Large',
            'hpp': 22000, 'price': 29000,
            'recipe': [('Tortilla Large', 1), ('Selada / Lettuce', 1), ('Ayam Filet Dada', 1), ('Sosis Sapi', 1), ('Telur', 1), ('Keju Slice Melt', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'SPC-BEF-REG', 'name': 'Special Beef', 'size': 'Regular',
            'hpp': 18000, 'price': 25000,
            'recipe': [('Tortilla Regular', 1), ('Selada / Lettuce', 1), ('Beef Smoke / Slice', 1), ('Sosis Sapi', 0.5), ('Telur', 1), ('Keju Slice Melt', 1), ('Saus & Mayo', 1)]
        },
        {
            'code': 'SPC-BEF-LRG', 'name': 'Special Beef', 'size': 'Large',
            'hpp': 23000, 'price': 30000,
            'recipe': [('Tortilla Large', 1), ('Selada / Lettuce', 1), ('Beef Smoke / Slice', 2), ('Sosis Sapi', 1), ('Telur', 1), ('Keju Slice Melt', 1), ('Saus & Mayo', 1)]
        },
    ]

    for m in menus_data:
        menu = MenuItem(
            code=m['code'],
            name=m['name'],
            size=m['size'],
            hpp_real=m['hpp'],
            selling_price=m['price'],
            is_active=True
        )
        db.session.add(menu)
        db.session.flush()

        for ing_name, qty in m['recipe']:
            if ing_name in ing_map:
                recipe_item = RecipeItem(
                    menu_id=menu.id,
                    ingredient_id=ing_map[ing_name],
                    quantity_needed=qty
                )
                db.session.add(recipe_item)

    db.session.commit()
    print('Seeding completed successfully!')
