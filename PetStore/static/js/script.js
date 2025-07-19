(function($) {

    "use strict";

    // Helper function to initialize preloader
   var initPreloader = function() {
    $(document).ready(function($) {
      var Body = $('body');
      Body.addClass('preloader-site');
    });
    // CHANGED: Use .on('load') instead of .load() for modern jQuery
    $(window).on('load', function() {
      $('.preloader-wrapper').fadeOut();
      $('body').removeClass('preloader-site');
    });
  }
    // Initialize Chocolat light box
    // Uses jQuery to select elements, then gets native DOM elements for Chocolat
    var initChocolat = function() {
        Chocolat($('.image-link').get(), { // .get() converts jQuery object to array of native DOM elements
            imageSize: 'contain',
            loop: true,
        });
    };

    // Initialize Swiper sliders
    // Swiper.js is a standalone library and is initialized with `new Swiper()`,
    // passing a native DOM element or selector string.
    var initSwiper = function() {
        // Swiper slider home 2
        $('.slideshow').each(function() {
            var space = $(this).attr('data-space') ? parseInt($(this).attr('data-space')) : 0;
            var col = $(this).attr('data-col');
            if (typeof col == "undefined" || !col) {
                col = 1;
            }

            var swiper = new Swiper(this, { // Pass 'this' (native DOM element) to Swiper
                slidesPerView: parseInt(col), // Ensure col is parsed as int
                spaceBetween: space,
                speed: 1000,
                loop: true,
                pagination: {
                    el: ".slideshow-swiper-pagination",
                    clickable: true,
                },
            });
        });

        var testimonialSwiper = new Swiper(".testimonial-swiper", {
            slidesPerView: 1,
            spaceBetween: 20,
            navigation: {
                nextEl: ".testimonial-button-next",
                prevEl: ".testimonial-button-prev",
            },
        });

        var brand_swiper = new Swiper(".brand-carousel", {
            slidesPerView: 4,
            spaceBetween: 30,
            speed: 500,
            navigation: {
                nextEl: ".brand-carousel-next",
                prevEl: ".brand-carousel-prev",
            },
            breakpoints: {
                0: {
                    slidesPerView: 2,
                },
                768: {
                    slidesPerView: 2,
                },
                991: {
                    slidesPerView: 3,
                },
                1500: {
                    slidesPerView: 4,
                },
            }
        });

        var productSwiper = new Swiper(".product-swiper", {
            spaceBetween: 20,
            pagination: {
                el: ".product-swiper-pagination",
                clickable: true,
            },
            breakpoints: {
                0: {
                    slidesPerView: 1,
                },
                660: {
                    slidesPerView: 3,
                },
                980: {
                    slidesPerView: 4,
                },
                1500: {
                    slidesPerView: 5,
                }
            },
        });

        var products_swiper = new Swiper(".products-carousel", {
            slidesPerView: 5,
            spaceBetween: 30,
            speed: 500,
            navigation: {
                nextEl: ".products-carousel-next",
                prevEl: ".products-carousel-prev",
            },
            breakpoints: {
                0: {
                    slidesPerView: 1,
                },
                768: {
                    slidesPerView: 3,
                },
                991: {
                    slidesPerView: 4,
                },
                1500: {
                    slidesPerView: 5,
                },
            }
        });

        // product single page
        var thumb_slider = new Swiper(".product-thumbnail-slider", {
            slidesPerView: 5,
            spaceBetween: 20,
            // autoplay: true,
            direction: "vertical",
            breakpoints: {
                0: {
                    direction: "horizontal"
                },
                992: {
                    direction: "vertical"
                },
            },
        });

        var large_slider = new Swiper(".product-large-slider", {
            slidesPerView: 1,
            // autoplay: true,
            spaceBetween: 0,
            effect: 'fade',
            thumbs: {
                swiper: thumb_slider,
            },
            pagination: {
                el: ".swiper-pagination",
                clickable: true,
            },
        });
    };

    // Animate Texts
    var initTextFx = function() {
        $('.txt-fx').each(function() {
            var newstr = '';
            var count = 0;
            var delay = 100;
            var stagger = 10;
            var words = this.textContent.split(/\s/);
            var arrWords = new Array();

            $.each(words, function(key, value) {
                newstr = '<span class="word">';

                for (var i = 0, l = value.length; i < l; i++) {
                    newstr += "<span class='letter' style='transition-delay:" + (delay + stagger * count) + "ms;'>" + value[i] + "</span>";
                    count++;
                }
                newstr += '</span>';

                arrWords.push(newstr);
                count++;
            });

            this.innerHTML = arrWords.join("<span class='letter' style='transition-delay:" + delay + "ms;'>&nbsp;</span>");
        });
    };

    // Input spinner
   var initProductQty = function() {
        $('.product-qty').each(function() {
            var $el_product = $(this);
            // Using .off().on() to prevent multiple bindings if initProductQty is called multiple times
            $el_product.find('.quantity-right-plus').off('click').on('click', function(e) {
                e.preventDefault();
                var $input = $el_product.find('.quantity');
                var currentQuantity = parseInt($input.val());
                var maxQuantity = parseInt($input.attr('max')); // Get max from the input's max attribute

                if (currentQuantity < maxQuantity) {
                    $input.val(currentQuantity + 1);
                }
            });

            $el_product.find('.quantity-left-minus').off('click').on('click', function(e) {
                e.preventDefault();
                var $input = $el_product.find('.quantity');
                var currentQuantity = parseInt($input.val());
                var minQuantity = parseInt($input.attr('min')); // Get min from the input's min attribute

                if (currentQuantity > minQuantity) {
                    $input.val(currentQuantity - 1);
                }
            });

            // Optional: Add change listener for direct input into the textbox
            $el_product.find('.quantity').off('change').on('change', function() {
                var $input = $(this);
                var value = parseInt($input.val());
                var min = parseInt($input.attr('min'));
                var max = parseInt($input.attr('max'));

                if (isNaN(value) || value < min) {
                    $input.val(min);
                } else if (value > max) {
                    $input.val(max);
                }
            });
        });
    };

    // Initialize jarallax parallax
    // Uses jQuery to select elements, then gets native DOM elements for jarallax
    var initJarallax = function() {
        jarallax($(".jarallax").get()); // .get() converts jQuery object to array of native DOM elements

        jarallax($(".jarallax-keep-img").get(), {
            keepImg: true,
        });
    };

    // Modal Quick View functionality
    var initProductQuickViewModal = function() {
        const $productQuickViewModal = $('#productQuickViewModal');
        const $modalProductContent = $('#modalProductContent');

        $productQuickViewModal.on('show.bs.modal', function(event) {
            const $button = $(event.relatedTarget);
            const productId = $button.data('product-id');
            $modalProductContent.html('<p>Loading product information...</p>');

            if (productId) {
                const fetchUrl = `/product-quick-view/${productId}/`;

                $.ajax({
                    url: fetchUrl,
                    method: 'GET',
                    dataType: 'html',
                    success: function(responseHtml) {
                        $modalProductContent.html(responseHtml);
                    },
                    error: function(xhr, status, error) {
                        console.error('Error fetching product details:', status, error);
                        $modalProductContent.html('<p class="text-danger">Failed to load product details. Please try again.</p>');
                    }
                });
            }
        });
    };

     var initModalProductQty = function() {
        // Use event delegation on the modal itself, as its content is dynamic
        // This ensures the event listeners work even after new content is loaded
        $('#productQuickViewModal').on('click', '.quantity-right-plus', function(e) {
            e.preventDefault();
            var $input = $(this).closest('.product-qty').find('.quantity');
            var currentQuantity = parseInt($input.val());
            var maxQuantity = parseInt($input.attr('max')); // Get max from the input's max attribute

            if (currentQuantity < maxQuantity) {
                $input.val(currentQuantity + 1);
            }
        });

        $('#productQuickViewModal').on('click', '.quantity-left-minus', function(e) {
            e.preventDefault();
            var $input = $(this).closest('.product-qty').find('.quantity');
            var currentQuantity = parseInt($input.val());
            var minQuantity = parseInt($input.attr('min')); // Get min from the input's min attribute

            if (currentQuantity > minQuantity) {
                $input.val(currentQuantity - 1);
            }
        });

        // Optional: Add change listener for direct input into the textbox within the modal
        $('#productQuickViewModal').on('change', '.quantity', function() {
            var $input = $(this);
            var value = parseInt($input.val());
            var min = parseInt($input.attr('min'));
            var max = parseInt($input.attr('max'));

            if (isNaN(value) || value < min) {
                $input.val(min);
            } else if (value > max) {
                $input.val(max);
            }
        });
    };

      // Function to get CSRF token from cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Function to update the global cart item count (e.g., in header)
    var updateCartCount = function(count) {
        $('#cart-item-count').text(count);
        if (count > 0) {
            $('#cart-item-count').removeClass('d-none'); // Show badge if items exist
        } else {
            $('#cart-item-count').addClass('d-none'); // Hide badge if no items
        }
    };

    
    var fetchAndRenderCartDetails = function() {
        const $cartDialogContent = $('#cart-dialog-content');
        const $cartDialogTotalPrice = $('#cart-dialog-total-price');

        $cartDialogContent.html('<p class="text-center text-muted">Loading cart...</p>'); // Show loading state

        $.ajax({
            url: '/get-cart-details/', // Your Django URL to get cart details
            method: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response.cart_items && response.cart_items.length > 0) {
                    let cartHtml = '<ul class="list-group list-group-flush">';
                    response.cart_items.forEach(item => {
                        cartHtml += `
                            <li class="list-group-item d-flex align-items-center">
                                <img src="${item.product_image_url || '/static/images/placeholder.png'}" alt="${item.product_name}" class="img-fluid me-3" style="width: 60px; height: 60px; object-fit: cover;">
                                <div class="flex-grow-1">
                                    <h6 class="mb-0">${item.product_name}</h6>
                                    <small class="text-muted">Quantity: ${item.quantity} | Price: $${item.price.toFixed(2)}</small>
                                </div>
                                <span class="fw-bold">$${item.total_item_price.toFixed(2)}</span>
                            </li>
                        `;
                    });
                    cartHtml += '</ul>';
                    $cartDialogContent.html(cartHtml);
                } else {
                    $cartDialogContent.html('<p class="text-center text-muted">Your cart is empty.</p>');
                }
                $cartDialogTotalPrice.text(`$${response.cart_total_price.toFixed(2)}`);
                updateCartCount(response.cart_total_items); // Update global counter
            },
            error: function(xhr, status, error) {
                console.error('Error fetching cart details:', status, error);
                $cartDialogContent.html('<p class="text-danger text-center">Failed to load cart. Please try again.</p>');
                updateCartCount(0); // Reset counter on error
            }
        });
    };

    // Handle 'Add to Cart' button clicks (event delegation for dynamic buttons)
    var initAddToCart = function() {
        $(document).on('click', '.btn-cart', function(e) {
            e.preventDefault();
            const $button = $(this);
            const productId = $button.data('product-id');
            // Check if the button is within a modal product view or main grid
            let quantity = 1; // Default quantity
            let $quantityInput = $button.closest('.button-area').find('.quantity');

            if ($quantityInput.length) {
                quantity = parseInt($quantityInput.val());
            }

            if (productId && quantity >= 1) {
                // Disable button and show loading state
                $button.prop('disabled', true).text('Adding...');

                $.ajax({
                    url: '/add-to-cart/', // Your Django URL for add to cart
                    method: 'POST',
                    data: JSON.stringify({
                        'product_id': productId,
                        'quantity': quantity
                    }),
                    contentType: 'application/json',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken') // Include CSRF token
                    },
                    success: function(response) {
                        if (response.success) {
                            alert(response.message); // Or use a nicer notification system
                            updateCartCount(response.cart_total_items);

                            // Optional: Close quick view modal if open
                            $('#productQuickViewModal').modal('hide');

                            // Open and refresh the cart dialog after adding
                            var cartDialog = new bootstrap.Modal(document.getElementById('cartDialogModal'));
                            cartDialog.show();
                            fetchAndRenderCartDetails(); // Refresh cart content

                        } else {
                            alert('Error: ' + response.error);
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error('Add to cart error:', status, error, xhr.responseText);
                        alert('Failed to add item to cart. Please try again.');
                    },
                    complete: function() {
                        // Re-enable button
                        $button.prop('disabled', false).html('<svg width="18" height="18"><use xlink:href="#cart"></use></svg> Add to Cart');
                    }
                });
            } else {
                alert('Invalid product ID or quantity.');
            }
        });

        // Event listener for when the cart dialog is shown
        $('#cartDialogModal').on('show.bs.modal', function() {
            fetchAndRenderCartDetails(); // Load cart content every time modal is opened
        });
    };

    // Document ready block (all initializations should go here)
    $(document).ready(function() {
        initPreloader();
        initTextFx();
        initSwiper();
        initProductQty();
        initJarallax();
        initChocolat();
        initProductQuickViewModal(); // Initialize the modal quick view
        initModalProductQty(); 
        initAddToCart(); 
        fetchAndRenderCartDetails();
    });

})(jQuery);