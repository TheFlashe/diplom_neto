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
