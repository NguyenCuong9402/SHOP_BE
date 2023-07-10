# coding: utf-8
import json
from typing import List

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
    type = db.Column(db.String(50), nullable=True)
    created_date = db.Column(db.Integer, default=0)
    picture = db.Column(db.Text(), nullable=True)


class Orders(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=True)
    phone_number = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    count = db.Column(db.Integer, nullable=True, default=0)
    created_date = db.Column(db.Integer, default=0)

    @hybrid_property
    def user_name(self):
        user = User.query.filter(User.id == self.user_id).first()
        return user.name_user

    @hybrid_property
    def order_items(self):
        order_items = OrderItems.query.filter(OrderItems.order_id == self.id)\
            .order_by(desc(OrderItems.created_date)).all()
        return order_items


class OrderItems(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.String(50), primary_key=True)
    product_id = db.Column(db.String(50), db.ForeignKey('product.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=False)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id', ondelete='CASCADE', onupdate='CASCADE'),
                         nullable=False)
    quantity = db.Column(db.Integer, nullable=True, default=1)
    count = db.Column(db.Integer, default=0)
    size = db.Column(db.String(5), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    created_date = db.Column(db.Integer, default=0)

    @hybrid_property
    def product_name(self):
        product = Product.query.filter(Product.id == self.product_id).first()
        return product.name


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(50), primary_key=True)
    email = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(100), nullable=True)
    name_user = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    phone_number = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    admin = db.Column(db.Integer, default=0)
    created_date = db.Column(db.Integer, default=0)
    picture = db.Column(db.Text(), nullable=True)
    count_money_buy = db.Column(db.Integer, default=0)


class CartItems(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.String(50), primary_key=True)
    product_id = db.Column(db.String(50), db.ForeignKey('product.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=True)
    quantity = db.Column(db.Integer, nullable=True, default=1)
    size = db.Column(db.String(5), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    created_date = db.Column(db.Integer, default=0)

    @hybrid_property
    def name_product(self):
        product = Product.query.filter(Product.id == self.product_id).first()
        return product.name

    @hybrid_property
    def price(self):
        product = Product.query.filter(Product.id == self.product_id).first()
        return product.price*self.quantity


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









