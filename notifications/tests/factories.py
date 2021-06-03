from factory.django import DjangoModelFactory


class NotificationTemplateFactory(DjangoModelFactory):
    class Meta:
        model = 'notifications.NotificationTemplate'

    title_fi = "Title fi"
    title_en = "Title en"
    body_fi = "Body fi"
    body_en = "Body en"
