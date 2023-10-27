# coding: utf-8
import json
from typing import List
from sqlalchemy import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, TEXT, asc, CheckConstraint, desc
from app.extensions import db
from sqlalchemy.dialects.mysql import INTEGER , DOUBLE
from sqlalchemy.ext.hybrid import hybrid_property


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message_id = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(255))
    show = db.Column(db.Boolean, default=0)
    duration = db.Column(db.Integer, default=5)
    status = db.Column(db.String(20), default='success')
    message = db.Column(db.String(500), nullable=False)
    dynamic = db.Column(db.Boolean, default=0)
    object = db.Column(db.String(255))


class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    price = db.Column(db.Integer, nullable=True, default=0)
    describe = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    phan_loai_id = db.Column(db.String(50), db.ForeignKey('phan_loai.id', ondelete='SET NULL',
                                                          onupdate='SET NULL'), nullable=True)
    created_date = db.Column(db.Integer, default=0)
    picture = db.Column(db.Text(), nullable=True)
    old_price = db.Column(db.Integer, nullable=True, default=0)
    giam_gia = db.Column(db.Integer, nullable=True, default=0)
    cac_mau = db.Column(db.JSON)

    @hybrid_property
    def reviews(self):
        reviews = Reviews.query.filter(Reviews.product_id == self.id).order_by(desc(Reviews.created_date)).all()
        return reviews

    @property
    def sold_count(self):
        sold_count = db.session.query(func.sum(OrderItems.quantity)).filter(OrderItems.product_id == self.id).scalar()
        if sold_count is None:
            sold_count = 0
        return sold_count


class Orders(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=True)
    phone_number = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    count = db.Column(db.Integer, nullable=True, default=0)
    created_date = db.Column(db.Integer, default=0)
    tinh = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    huyen = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    xa = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    loi_nhan = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    ship_id = db.Column(db.String(50), db.ForeignKey('shipper.id', ondelete='SET NULL', onupdate='SET NULL'),
                        nullable=True)
    gia_ship = db.Column(db.Integer, nullable=True)
    tong_thanh_toan = db.Column(db.Integer, nullable=True)
    trang_thai = db.Column(db.Boolean, default=0)  # 0: Chưa lên đơn ,  1: đã lên đơn

    @hybrid_property
    def user_name(self):
        user = User.query.filter(User.id == self.user_id).first()

        return user.name_user if user is not None else "Người dùng đã xóa tài khoản"

    @hybrid_property
    def order_items(self):
        order_items = OrderItems.query.filter(OrderItems.order_id == self.id)\
            .order_by(desc(OrderItems.created_date)).all()
        return order_items

    @hybrid_property
    def don_vi_ship(self):
        ship = Shipper.query.filter(Shipper.id == self.ship_id).first()
        return  ship.name if ship is not None else 'Đã ngừng hoạt động'


class OrderItems(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.String(50), primary_key=True)
    product_id = db.Column(db.String(50), db.ForeignKey('product.id', ondelete='SET NULL', onupdate='SET NULL'),
                           nullable=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id', ondelete='CASCADE', onupdate='CASCADE'),
                         nullable=False)
    quantity = db.Column(db.Integer, nullable=True, default=1)
    count = db.Column(db.Integer, default=0)
    size = db.Column(db.String(5), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    created_date = db.Column(db.Integer, default=0)

    @hybrid_property
    def product_name(self):
        if self.product_id is None or self.product_id == "":
            return "sản phẩm đã bị xóa"
        else:
            product = Product.query.filter(Product.id == self.product_id).first()
            return product.name


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(50), primary_key=True)
    email = db.Column(db.String(100), nullable=True)
    birthday = db.Column(db.Date)
    password = db.Column(db.String(100), nullable=True)
    name_user = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    phone_number = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    tinh = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    huyen = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    xa = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)

    gender = db.Column(db.Boolean, nullable=True)  # 0: Nam , Nu : 1
    admin = db.Column(db.Integer, default=0)
    created_date = db.Column(db.Integer, default=0)
    picture = db.Column(db.Text(), nullable=True)


class CartItems(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.String(50), primary_key=True)
    product_id = db.Column(db.String(50), db.ForeignKey('product.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=True)
    quantity = db.Column(db.Integer, nullable=True, default=1)
    size = db.Column(db.String(5), nullable=True)
    color = db.Column(db.String(50, collation="utf8mb4_vietnamese_ci"), nullable=True)
    created_date = db.Column(db.Integer, default=0)

    @hybrid_property
    def name_product(self):
        product = Product.query.filter(Product.id == self.product_id).first()
        return product.name

    @hybrid_property
    def price(self):
        product = Product.query.filter(Product.id == self.product_id).first()
        return product.price

    @hybrid_property
    def total(self):
        product = Product.query.filter(Product.id == self.product_id).first()
        return product.price*self.quantity

    @hybrid_property
    def cac_mau(self):
        product = Product.query.filter(Product.id == self.product_id).first()
        return product.cac_mau


class Reviews(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.String(50), primary_key=True)
    product_id = db.Column(db.String(50), db.ForeignKey('product.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=True)
    comment = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    created_date = db.Column(db.Integer, default=0)

    @hybrid_property
    def user_name(self):
        user = User.query.filter(User.id == self.user_id).first()
        return user.name_user


class PhanLoai(db.Model):
    __tablename__ = 'phan_loai'
    id = db.Column(db.String(50), primary_key=True)
    key = db.Column(db.Text)
    name = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    parent_id = db.Column(db.String(50), db.ForeignKey('phan_loai.id', ondelete='CASCADE', onupdate='CASCADE'),
                          nullable=True)


class DiaChiVN(db.Model):
    __tablename__ = 'dia_chi'
    id = db.Column(db.String(50), primary_key=True)
    tinh = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    huyen = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    xa = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)


class Shipper(db.Model):
    __tablename__ = 'shipper'
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    gia_ship = db.Column(db.Integer, default=1)







