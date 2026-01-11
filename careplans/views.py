from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import OrderIntakeForm


def intake_order(request):
    if request.method == "POST":
        form = OrderIntakeForm(request.POST)
        if form.is_valid():
            order = form.save()
            if order.is_possible_duplicate_order or (order.duplicate_reason):
                messages.warning(request, f"Saved with warning: {order.duplicate_reason}")
            else:
                messages.success(request, "Order created successfully.")
            return redirect("intake_order")
    else:
        form = OrderIntakeForm()

    return render(request, "careplans/intake.html", {"form": form})
