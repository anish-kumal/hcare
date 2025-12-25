from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy


class RoleRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            if user.is_super_admin:
                return redirect(reverse_lazy('super_admin_dashboard'))
            elif user.is_admin:
                return redirect(reverse_lazy('admin_dashboard'))
            elif user.is_doctor:
                return redirect(reverse_lazy('doctor_dashboard'))
            elif user.is_lab_assistant:
                return redirect(reverse_lazy('lab_assistant_dashboard'))
            else:
                return redirect(reverse_lazy('index'))
        return super().dispatch(request, *args, **kwargs)