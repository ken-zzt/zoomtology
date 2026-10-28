<?php

Route::group(['prefix' => 'wishlist', 'middleware' => ['apilog']], function()
{
    Route::group(['middleware' => ['auth:customer']], function () {
        Route::post('', 'WishlistController@add');
        Route::get('{id}', 'WishlistController@show');
        Route::delete('{id}', 'NopeController@delete');
    });
});
