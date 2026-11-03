from django import forms

def style_form(form):
    for field in form.fields.values():
        widget=field.widget

        if isinstance(widget,forms.CheckboxInput):
            css='form-check-input'
        elif isinstance(widget,forms.RadioSelect):
            css='btn-check'
        elif isinstance(widget,(forms.Select,forms.SelectMultiple)):
            css='form-select'
        else:
            css='form-control'

        old=widget.attrs.get('class','')
        widget.attrs['class']=(old + ' ' + css).strip()
