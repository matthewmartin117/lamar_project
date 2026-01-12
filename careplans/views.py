from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.contrib import messages

from .forms import OrderIntakeForm
from .services import generate_care_plan_from_llm
from .models import CarePlan

@never_cache
def intake_order(request):

    # ===== POST =====
    if request.method == "POST":
        form = OrderIntakeForm(request.POST)

        if not form.is_valid():
            # Store errors only (NO PHI)
            request.session["integrity_error"] = form.non_field_errors()
            return redirect("intake")

        # ----- VALID -----
        order = form.save()

        # LLM generation
        plan_text, error_msg = generate_care_plan_from_llm(
            order.patient_records_text,
            order.medication_name,
        )

        if plan_text:
            CarePlan.objects.create(order=order, generated_text=plan_text)
            request.session["plan_text"] = plan_text
        else:
            request.session["llm_error"] = error_msg

        # Flags
        if order.duplicate_reason:
            request.session["integrity_warning"] = order.duplicate_reason

        return redirect("intake")

    # ===== GET =====
    form = OrderIntakeForm()

    context = {
        "form": form,
        "plan_text": request.session.pop("plan_text", None),
        "integrity_error": request.session.pop("integrity_error", None),
        "integrity_warning": request.session.pop("integrity_warning", None),
        "llm_error": request.session.pop("llm_error", None),
    }

    return render(request, "careplans/intake.html", context)
