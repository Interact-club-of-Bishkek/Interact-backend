from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import Volunteer

class VolunteerCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput, required=False)

    class Meta:
        model = Volunteer
        fields = ('login', 'name', 'phone_number')

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")

        # Проверка паролей, только если хоть что-то введено
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Пароли не совпадают.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")

        if password:
            user.set_password(password)
            user.visible_password = password
        else:
            # при отсутствии пароля — сгенерируем его в модели при save
            pass

        if commit:
            user.save()
        return user


class VolunteerChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label="Пароль (хеш)")

    class Meta:
        model = Volunteer
        fields = ('login', 'password', 'name', 'phone_number', 'is_active', 'is_staff', 'is_superuser')

    def clean_password(self):
        # Возвращаем изначальный пароль, без изменений
        return self.initial["password"]
