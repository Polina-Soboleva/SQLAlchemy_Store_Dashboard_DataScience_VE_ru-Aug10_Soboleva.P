import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, func, insert, update
from sqlalchemy.orm import Session
from models import User, Product, Order

load_dotenv()

def get_engine():
    """Create and return a SQLAlchemy engine from DATABASE_URL."""
    url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL is not set")

    engine = create_engine(url)

    try:
        with engine.connect():
            pass
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        exit(1)

    return engine

def store_report(engine):

    with Session(engine) as session:
        # Read: every admin, as User objects
        user_count = session.scalar(
            select(func.count(User.id))
        )

        product_count = session.scalar(
            select(func.count(Product.id))
        )

        order_count = session.scalar(
            select(func.count(Order.id))
        )
        print(f"=== Store Dashboard ===\nUsers: {user_count} | Product: {product_count} | Orders: {order_count}")

        print("\nCatalog:\n")
        catalog = session.execute(
            select(Product.name, Product.price, Product.stock)
            .order_by(Product.name)
        )

        for name, price, stock in catalog:
            print(f"{name:<30}${price:<7.2f}  (stock {stock})")
        print("\nTop customers:\n")
        customer_orders = session.execute(
            select(
                User.email, func.sum(Order.quantity))
                .join(Order, Order.user_id == User.id)
                .group_by(User.email)
                .order_by(func.sum(Order.quantity).desc())
                .limit(3)
        )

        for  email, orders_num in customer_orders:
            if orders_num == 1:
                print(f"{email:<30}- {orders_num} item")
            else:
                print(f"{email:<30}- {orders_num} items")

def menu_add_product(engine):
    """Меню для добавления продукта"""
    
    name = input("Введи название продукта: ")
    category = input("Введи название категории: ")

    while True:
        try:
            price = float(input("Введи цену: "))
            break
        except ValueError:
            print("Некорректный ввод. Введите число, например: 12 или 12.6")

    while True:
        try:
            stock = int(input("Введи кол-во: "))
            break
        except ValueError:
            print("Некорректный ввод. Введите число, например: 12")

    add_product(engine, name, category, price, stock)

def add_product(engine, name, category, price, stock):
    """INSERT a product and return its new id."""

    with engine.begin() as conn:   # begin() commits automatically at the end
        new_product = conn.execute(
            insert(Product).returning(Product.id),
            {
                "name": name,
                "category": category,
                "price": price,
                "stock": stock
            }
        )
        #raise ValueError("Некорректные данные")
        print (f"New product ID: {new_product.scalar()}")

def menu_place_order(engine):
    """Меню для добавления заказа"""

    while True:
        email = input("Введи email клиента: ")

        with Session(engine) as conn:
            user_id = conn.scalar(
            select(User.id)
            .where(User.email == email)
            )

        if user_id is None:
            print("Клиент не найден")
            continue

        break
            
    while True:
        product_name = input("Введи название продукта: ")

        with Session(engine) as conn:
            product_id = conn.scalar(
            select(Product.id)
            .where(Product.name == product_name)
            )

        if product_id is None:
            print("Продукт не найден")
            continue
        break

    while True:
        try:
            quantity = int(input("Введи кол-во продукта: "))
            break
        except ValueError:
            print("Некорректный ввод. Введите число, например: 12")

    place_order(engine, user_id, product_id, quantity)

def place_order(engine, user_id, product_id, quantity):
    """Create an order and decrement stock in one transaction."""

    with engine.begin() as conn:   # begin() commits on success, rolls back on error
        stock_quantity = conn.scalar(
            select(Product.stock)
            .where(Product.id == product_id)
        )

        if stock_quantity >= quantity:
            new_order = conn.execute(
                insert(Order).returning(Order.id),
                {
                    "user_id": user_id,
                    "product_id": product_id,
                    "quantity": quantity
                }
            )
            print (f"New order ID: {new_order.scalar()}")

        else: print("Недостаточно товара на складе")

def get_low_stock_products(engine):
    """Товары с остатком меньше 10"""

    with Session(engine) as session:
        rest_stock = session.execute(
            select(
                Product.id, Product.name, Product.stock)
                .where(Product.stock <= 10)
                ).all()
        
        if not rest_stock:
            print("Товара с остатком меньше 10 нет")

        else:
            print("\nТовары с остатком меньше 10:")
            print(f"{'ID':<5} {'Название продукта':<35} {'Остаток':>8}")
            print("-" * 50)

            for product_id, name, stock in rest_stock:
                print(f"{product_id:<5} {name:<35} {stock:>8}")

def get_product_revenue(engine):
    """Выручка по каждому товару"""

    with Session(engine) as session:
        product_revenue = session.execute(
            select(Product.id, Product.name, Product.price * func.sum(Order.quantity))
                    .join(Order, Order.product_id == Product.id)
                    .where(Order.status != 'Cancelled')
                    .group_by(Product.id, Product.name, Product.price)
                    .order_by(Product.price * func.sum(Order.quantity).desc())
            )
        print("\nВыручка")
        print("-" * 50)
        print(f"{'ID':<5} {'Название продукта':<35} {'Выручка':>8}")

        for id,  product_name, revenue in product_revenue:
            print(f"{id:<5} {product_name:<35} {revenue:>8}")

def get_user_without_orders(engine):
    """Пользователи без заказов"""

    with Session(engine) as session:
        user_without_orders = session.execute(
            select(User.id, User.full_name)
            .outerjoin(Order, Order.user_id == User.id) 
            .where(Order.id.is_(None))
        ).all()

        if not user_without_orders:
            print('Все пользователи имеют заказы')

        else:
            print(f"\nПользователи без заказов:")
            print("-" * 50)
            print(f"{'ID':<7} {'Имя'}")
            for id, name in user_without_orders:
                print(f"{id:<7} {name}")

def main():
    engine = get_engine()
    store_report(engine)
    menu_add_product(engine)
    menu_place_order(engine)
    get_low_stock_products(engine)
    get_product_revenue(engine)
    get_user_without_orders(engine)

if __name__ == "__main__":
    main()
