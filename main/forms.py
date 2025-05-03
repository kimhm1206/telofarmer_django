from django import forms
from django.contrib.auth.models import User
from django.conf import settings

class TelofarmSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    staff_code = forms.CharField(label="텔로팜 직원 코드")

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get("password")
        cpw = cleaned_data.get("confirm_password")
        code = cleaned_data.get("staff_code")

        if pw != cpw:
            raise forms.ValidationError("비밀번호가 일치하지 않습니다.")
        if code != settings.TELOFARM_MEMBER_CODE:
            raise forms.ValidationError("직원 코드가 올바르지 않습니다.")
        return cleaned_data