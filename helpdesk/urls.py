from django.urls import path
from . import views

urlpatterns=[
    path('inbox/',views.inbox,name='inbox'),
    path('course/<int:course_id>/',views.request_list,name='request_list'),
    path('topic/<int:topic_id>/new/',views.new_request,name='new_request'),
    path('<int:request_id>/',views.request_detail,name='request_detail'),
    path('<int:request_id>/edit/',views.edit_request,name='edit_request'),
    path('<int:request_id>/cancel/',views.cancel_request,name='cancel_request'),
    path('<int:request_id>/resolve/',views.resolve_request,name='resolve_request'),
    path('<int:request_id>/feedback/',views.give_feedback,name='give_feedback'),
    path('<int:request_id>/step-back/',views.step_back,name='step_back'),
    path('<int:request_id>/invite/<int:helper_id>/',views.invite_helper,name='invite_helper'),
    path('invitations/<int:invitation_id>/accept/',views.accept_invitation,name='accept_invitation'),
    path('invitations/<int:invitation_id>/decline/',views.decline_invitation,name='decline_invitation'),
    path('invitations/<int:invitation_id>/withdraw/',views.withdraw_invitation,name='withdraw_invitation'),
    path('responses/<int:response_id>/delete/',views.delete_response,name='delete_response'),
]
