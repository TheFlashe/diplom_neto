from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify

User = get_user_model()


class Shop(models.Model):
    name = models.CharField(max_length=50, db_index=True)
    slug = models.SlugField(max_length=50, blank=True, unique=True)
    description = models.CharField(max_length=200, blank=True)
    url = models.URLField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ownee_shops')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shop'
        verbose_name = 'Shop'
        verbose_name_plural = 'Shops'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} (владелец: {self.owner})'


class Category(models.Model):
    name = models.CharField(max_length=50, db_index=True)
    slug = models.SlugField(max_length=50, blank=True, unique=True)
    shops = models.ManyToManyField(Shop, related_name='categories')

    class Meta:
        ordering = ('name',)
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True)
    slug = models.SlugField(max_length=150, blank=True, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')

    class Meta:
        ordering = ('name',)
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    slug = models.SlugField(max_length=150, blank=True, unique=True, db_index=True)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    price_rrc = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_info')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='product_info')

    class Meta:
        ordering = ('name',)
        verbose_name = 'ProductInfo'
        verbose_name_plural = 'ProductsInfo'
        unique_together = ['product', 'shop']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Parameter(models.Model):
    name = models.CharField(max_length=100, verbose_name='param`s name')

    class Meta:
        verbose_name = 'Parameter'
        verbose_name_plural = 'Parameters'

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    value = models.CharField(max_length=100)
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name='product_parameters')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name='product_parameters')

    class Meta:
        verbose_name = 'ProductParameter'
        verbose_name_plural = 'ProductsParameters'
        constraints = [models.UniqueConstraint(fields=['product_info', 'parameter'],
                                               name='unique_product_parameter'), ]

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('basket', 'В корзине'),
        ('new', 'Новый'),
        ('confirmed', 'Подтвержден'),
        ('assembled', 'Собран'),
        ('sent', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('canceled', 'Отменен'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='User'
    )
    dt = models.DateTimeField(auto_now_add=True, verbose_name='Date created')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='basket',
        verbose_name='Status'
    )

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ('-dt',)

    def __str__(self):
        return f"Заказ #{self.id} от {self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Order'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Product'
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        verbose_name='Shop'
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='quantity')

    class Meta:
        verbose_name = 'Order item'
        verbose_name_plural = 'Order items'
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product', 'shop'],
                name='unique_order_item'
            ),
        ]

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class Contact(models.Model):

    TYPE_CHOICES = [
        ('phone', 'Телефон'),
        ('email', 'Email'),
        ('address', 'Адрес'),
    ]

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name='Type'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contacts',
        verbose_name='User'
    )
    value = models.CharField(max_length=200, verbose_name='value')

    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'

    def __str__(self):
        return f"{self.get_type_display()}: {self.value}"
