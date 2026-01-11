from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import OrderIntakeForm
from .services import generate_care_plan_from_llm
from .models import CarePlan

# handle form submission
def intake_order(request):
    if request.method == "POST":
        form = OrderIntakeForm(request.POST)
        if form.is_valid():
            # happy path: can proceed if the form is valid
            order = form.save()

            # Trigger LLM call
            plan_text, error_msg = generate_care_plan_from_llm(
                order.patient_records_text,
                order. medication_name
            )

            # happy path: sucessful LLM call with plan generated
            if plan_text:
                # Save the successful result to CarePlan model
                CarePlan.objects.create(order=order, generated_text=plan_text)
                messages.success(request, "Care plan generated successfully.")
            # unhappy path: LLM call is unsucessful
            else:
                # Handle the 'Safe Error' requirement
                messages.error(request, error_msg)

            # alternate path: flagging orders that could be possible duplicates:
            if order.is_possible_duplicate_order or (order.duplicate_reason):
                messages.warning(request, f"Saved with warning: {order.duplicate_reason}")
            else:
                messages.success(request, "Order created successfully.")
            return redirect("intake_order")
    else:
        form = OrderIntakeForm()

    return render(request, "careplans/intake.html", {"form": form})
